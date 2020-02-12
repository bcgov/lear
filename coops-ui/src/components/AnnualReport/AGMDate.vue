<template>
  <v-card flat class="agm-date-container">
    <div class="meta-container">
      <label>
        <span>Annual General<br>Meeting Date</span>
      </label>

      <v-form ref="form" class="value date">
        <v-menu
          ref="menu"
          v-model="menu"
          :close-on-content-click="false"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          max-width="290"
        >
          <template v-slot:activator="{ on }">
            <v-text-field
              data-test-id="agm-date-text"
              v-model="dateText"
              :disabled="noAgm"
              :rules="agmDateRules"
              label="Annual General Meeting Date"
              placeholder="Select your Annual General Meeting Date"
              prepend-icon="mdi-calendar"
              v-on="on"
              readonly
              filled
            />
          </template>
          <v-date-picker
            data-test-id="agm-date-picker"
            v-model="datePicker"
            :min=minDate
            :max=maxDate
            no-title
            @input="menu=false"
            @change="onDatePickerChanged($event)"
          />
        </v-menu>

        <!-- only display this info if a date has been selected -->
        <div class="validationErrorInfo" v-if="dateText">
          <span v-if="!allowCOA && !allowCOD">
            You can not change your Registered Office Addresses or Directors in this Annual Report because your AGM
            predates another filing that may have conflicting changes.
          </span>
          <span v-else-if="!allowCOA">
            You can not change your Registered Office Addresses in this Annual Report because your AGM predates another
            filing that may have conflicting changes.
          </span>
          <span v-else-if="!allowCOD">
            You can not change your Directors in this Annual Report because your AGM predates another
            filing that may have conflicting changes.
          </span>
        </div>
      </v-form>
    </div>

    <!-- don't show checkbox in current year -->
    <v-checkbox id="agm-checkbox"
      v-if="this.ARFilingYear && this.ARFilingYear < this.currentYear"
      v-model="noAgm"
      :label=checkBoxLabel
      @change="onCheckboxChanged($event)"
    />
  </v-card>
</template>

<script lang="ts">
import { Component, Mixins, Vue, Prop, Watch, Emit } from 'vue-property-decorator'
import { mapState, mapGetters } from 'vuex'
import DateMixin from '@/mixins/date-mixin'
import { FormType } from '@/interfaces'

@Component({
  mixins: [DateMixin],
  computed: {
    // Property definitions for runtime environment.
    ...mapState(['ARFilingYear', 'currentDate', 'lastPreLoadFilingDate', 'lastAnnualReportDate']),
    ...mapGetters(['lastFilingDate'])
  }
})
export default class AgmDate extends Mixins(DateMixin) {
  // annotate form to fix "Property X does not exist on type Y" error
  $refs!: {
    form: FormType
  }
  // Prop passed into this component.
  @Prop({ default: null })
  private newAgmDate: string | null

  @Prop({ default: null })
  private newNoAgm: string | null

  @Prop({ default: true })
  private allowCOA: boolean

  @Prop({ default: true })
  private allowCOD: boolean

  // Local properties.
  private dateText: string = '' // value in text field
  private datePicker: string = '' // value in date picker
  private menu: boolean = false // whether calendar menu is visible
  private noAgm: boolean = false // whether checkbox is checked
  private backupDate: string = '' // for toggling No AGM

  // Local definitions of computed properties for static type checking.
  // Use non-null assertion operator to allow use before assignment.
  readonly ARFilingYear!: number
  readonly currentDate!: string
  readonly lastPreLoadFilingDate!: string
  readonly lastFilingDate!: string
  readonly lastAnnualReportDate!: string

  /**
   * The array of validations rules for the AGM Date text field.
   */
  private get agmDateRules (): Array<Function> {
    return [
      v => this.noAgm || !!v || 'An Annual General Meeting date is required.'
    ]
  }

  /**
   * The label for the checkbox.
   */
  private get checkBoxLabel (): string {
    return 'We did not hold an Annual General Meeting in ' + this.ARFilingYear
  }

  /**
   * The maximum date that can be entered.
   */
  private get maxDate (): string {
    /*
     * If filing is in past year then use last day in that year,
     * otherwise use current date.
     */
    return (this.ARFilingYear < this.currentYear) ? `${this.ARFilingYear}-12-31` : this.currentDate
  }

  /**
   * The minimum date that can be entered.
   */
  private get minDate (): string {
    /*
     * Determine the latest of the following dates:
     * - the first day of the AR filing year
     * - the last Annual Report date
     */
    const firstDayOfYear = +`${this.ARFilingYear}-01-01`.split('-').join('')
    const lastAnnualReportDate = this.lastAnnualReportDate ? +this.lastAnnualReportDate.split('-').join('') : 0
    return this.numToUsableString(Math.max(firstDayOfYear, lastAnnualReportDate))
  }

  /**
   * The current year.
   */
  private get currentYear (): number {
    return this.currentDate ? +this.currentDate.substring(0, 4) : 0
  }

  /**
   * Called when component is mounted.
   */
  private mounted (): void {
    // initialize date picker but not text field
    this.datePicker = this.newAgmDate || this.maxDate
  }

  /**
   * Called when prop changes (ie, due to resuming a draft).
   */
  @Watch('newAgmDate')
  private onNewAgmDateChanged (val: string): void {
    // always update text field
    this.dateText = val
    // only update date picker if we have a valid date
    if (val) this.datePicker = val
    // update parent
    this.emitAgmDate()
    this.emitValid()
  }

  /**
   * Called when prop changes (ie, due to resuming a draft)
   */
  @Watch('newNoAgm')
  private onNewNoAgmChanged (val: boolean): void {
    // update model value
    this.noAgm = val
    // update parent
    this.emitNoAgm()
    this.emitValid()
  }

  /**
   * Called when date picker changes.
   */
  private onDatePickerChanged (val: string): void {
    // update text field
    this.dateText = val
    // update parent
    this.emitAgmDate()
    this.emitValid()
  }

  /**
   * Called when checkbox changes.
   */
  private onCheckboxChanged (val: boolean): void {
    if (val) {
      // save and clear text field
      this.backupDate = this.dateText
      this.dateText = ''
    } else {
      // restore text field
      this.dateText = this.backupDate
    }
    // trigger validation to display any errors
    this.$refs.form.validate()
    // update parent
    this.emitAgmDate()
    this.emitNoAgm()
    this.emitValid()
  }

  /**
   * Emits an event with the new value of AGM Date (from text field, which may be empty).
   */
  @Emit('agmDate')
  private emitAgmDate (): string {
    return this.dateText
  }

  /**
   * Emits an event with the new value of No AGM.
   */
  @Emit('noAgm')
  private emitNoAgm (): boolean {
    return this.noAgm
  }

  /**
   * Emits an event indicating whether or not this component is valid.
   * This needs to be called after all changes.
   */
  @Emit('valid')
  private emitValid (): boolean {
    return this.noAgm || !!this.dateText
  }
}
</script>

<style lang="scss" scoped>
// @import "@/assets/styles/theme.scss";

.agm-date-container {
  padding: 1.25rem;
}

.validationErrorInfo {
  color: red;
}

.value.date {
  .v-text-field {
    min-width: 25rem;
  }
}

.meta-container {
  display: flex;
  flex-flow: column nowrap;
  position: relative;

  > label:first-child {
    font-weight: 700;
  }
}

@media (min-width: 768px) {
  .meta-container {
    flex-flow: row nowrap;

    > label:first-child {
      flex: 0 0 auto;
      padding-right: 2rem;
      width: 12rem;
    }
  }
}

::v-deep .v-input--checkbox .v-label {
  color: rgba(0,0,0,0.87);
}
</style>
