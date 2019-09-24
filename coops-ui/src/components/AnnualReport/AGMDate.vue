<template>
  <v-card flat class="container">
    <div class="meta-container">
      <label>
        <span>Annual General<br>Meeting Date</span>
      </label>

      <div class="value date">
        <v-menu
          ref="menu"
          v-model="menu"
          :nudge-right="40"
          lazy
          transition="scale-transition"
          offset-y
          full-width
          min-width="18rem">
          <template v-slot:activator="{ on }">
            <v-text-field
              id="agm-textfield"
              v-model="dateFormatted"
              :disabled="didNotHoldAgm"
              :rules="agmDateRules"
              label="Enter your Annual General Meeting Date"
              hint="YYYY/MM/DD"
              append-icon="event"
              v-on="on"
              box>
            </v-text-field>
          </template>
          <v-date-picker
            id="agm-datepicker"
            v-model="date"
            :min=minDate
            :max=maxDate
            no-title
            @input="menu = true">
          </v-date-picker>
        </v-menu>

        <div class="validationErrorInfo" v-if="$v.dateFormatted.isNotNull">
          <span v-if="!$v.dateFormatted.isValidFormat">
            Date must be in format YYYY/MM/DD.
          </span>
          <span v-else-if="!$v.dateFormatted.isValidYear">
            Please enter a year within {{ARFilingYear}}.
          </span>
          <span v-else-if="!$v.dateFormatted.isValidMonth">
            Please enter a month between {{formatDate(minDate)}} and {{formatDate(maxDate)}}.
          </span>
          <span v-else-if="!$v.dateFormatted.isValidDay">
            Please enter a day between {{formatDate(minDate)}} and {{formatDate(maxDate)}}.
          </span>
          <span v-else-if="!allowCOA&&!allowCOD">
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
      </div>
    </div>

    <!-- don't show checkbox in current year -->
    <v-checkbox id="agm-checkbox"
      v-if="this.ARFilingYear && this.ARFilingYear < this.currentYear"
      v-model="didNotHoldAgm"
      :label=checkBoxLabel
    />
  </v-card>
</template>

<script lang="ts">

import { Component, Mixins, Vue, Prop, Watch, Emit } from 'vue-property-decorator'
import { isNotNull, isValidFormat, isValidYear, isValidMonth, isValidDay } from '@/validators'
import { mapState, mapGetters } from 'vuex'
import DateMixin from '@/mixins/date-mixin'

@Component({
  mixins: [DateMixin],
  computed: {
    // Property definitions for runtime environment.
    ...mapState(['ARFilingYear', 'currentDate', 'lastPreLoadFilingDate']),
    ...mapGetters(['lastFilingDate'])
  },
  validations: {
    dateFormatted: { isNotNull, isValidFormat, isValidYear, isValidMonth, isValidDay }
  }
})
export default class AGMDate extends Mixins(DateMixin) {
  // Prop passed into this component.
  @Prop({ default: '' })
  private initialAgmDate: string

  @Prop({ default: true })
  private allowCOA: boolean

  @Prop({ default: true })
  private allowCOD: boolean

  // Local properties.
  private date: string = '' // bound to date picker
  private dateFormatted: string = '' // bound to text field
  private menu: boolean = false // bound to calendar menu
  private didNotHoldAgm: boolean = false // bound to checkbox

  // Local definitions of computed properties for static type checking.
  // Use non-null assertion operator to allow use before assignment.
  readonly ARFilingYear!: number
  readonly currentDate!: string
  readonly lastPreLoadFilingDate!: string
  readonly lastFilingDate!: string

  /**
   * Computed value.
   * @returns The array of validations rules for the AGM Date text field.
   */
  private get agmDateRules (): Array<Function> {
    return [
      v => this.didNotHoldAgm || isNotNull(v) || 'An Annual General Meeting date is required.'
    ]
  }

  /**
   * Computed value.
   * @returns The label for the checkbox.
   */
  private get checkBoxLabel (): string {
    return 'We did not hold an Annual General Meeting in ' + this.ARFilingYear
  }

  /**
   * Computed value.
   * @returns The maximum date that can be entered.
   */
  private get maxDate (): string {
    return (this.ARFilingYear === this.currentYear)
      ? this.currentDate.split('/').join('-')
      : `${this.ARFilingYear}-12-31`
  }

  /**
   * Computed value.
   * @returns The minimum date that can be entered.
   */
  private get minDate (): string {
    /**
     * Determine the latest of the following dates:
     * - the first day of the AR filing year
     * - the last filing in filing history (from the Legal DB)
     * - the last pre-load Cobrs filing
     */
    const firstDayOfYear = +`${this.ARFilingYear}-01-01`.split('-').join('')
    const lastFilingDate = this.lastFilingDate ? +this.lastFilingDate.split('-').join('') : 0
    const lastPreLoadFilingDate = this.lastPreLoadFilingDate ? +this.lastPreLoadFilingDate.split('-').join('') : 0
    const minAgmDate = Math.max(firstDayOfYear, lastFilingDate, lastPreLoadFilingDate)
    return this.numToUsableString(minAgmDate)
  }

  /**
   * Computed value.
   * @returns The current year.
   */
  private get currentYear (): number {
    return this.currentDate ? +this.currentDate.substring(0, 4) : null
  }

  /**
   * Lifecycle hook to load initial data.
   */
  private mounted (): void {
    this.dateFormatted = this.formatDate(this.minDate)
  }

  /**
   * Local helper to change date from YYYY-MM-DD to YYYY/MM/DD.
   * @returns The formatted date.
   */
  private formatDate (date: string): string {
    if (!this.isValidDate(date, '-')) return ''
    const [year, month, day] = date.split('-')
    return `${year}/${month}/${day}`
  }

  /**
   * Local helper to change date from YYYY/MM/DD to YYYY-MM-DD.
   * @returns The parsed date.
   */
  private parseDate (date: string): string {
    // changes date from YYYY/MM/DD to YYYY-MM-DD
    if (!this.isValidDate(date, '/')) return ''
    const [year, month, day] = date.split('/')
    return `${year}-${month}-${day}`
  }

  /**
   * Local helper to determine if passed-in date is valid.
   * @returns True if date is valid, otherwise false.
   */
  private isValidDate (date, separator): boolean {
    return (isNotNull.call(this, date) &&
      isValidFormat.call(this, date, separator) &&
      isValidYear.call(this, date) &&
      isValidMonth.call(this, date) &&
      isValidDay.call(this, date))
  }

  /**
   * When prop changes, load (initial) data.
   */
  @Watch('initialAgmDate')
  private onInitialAgmDateChanged (val: string): void {
    if (val) {
      this.dateFormatted = this.formatDate(val)
    } else {
      this.didNotHoldAgm = true
    }
  }

  /**
   * When text field changes, update date picker.
   */
  @Watch('dateFormatted')
  private onDateFormattedChanged (val: string): void {
    this.date = this.parseDate(val)
    // NB: let date watcher update parent
  }

  /**
   * When date picker changes, update text field etc.
   */
  @Watch('date')
  private onDateChanged (val: string): void {
    const agmDate = this.isValidDate(val, '-') ? val : null
    // only update text field if date is valid
    // this is to retain previous invalid values
    if (agmDate) {
      this.dateFormatted = this.formatDate(val)
    }
    this.emitAgmDate(agmDate)
    this.emitValid(Boolean(this.didNotHoldAgm || agmDate))
  }

  /**
   * When checkbox changes, update text field etc.
   */
  @Watch('didNotHoldAgm')
  private onDidNotHoldAgmChanged (val: boolean): void {
    if (val) {
      // clear text field value
      this.dateFormatted = null
    } else {
      // reset text field value
      this.dateFormatted = this.formatDate(this.initialAgmDate || this.minDate)
    }
    this.emitNoAGM(val)
    this.emitValid(Boolean(this.didNotHoldAgm || this.dateFormatted))
  }

  /**
   * Emits an event with the new value of AGM Date.
   */
  @Emit('agmDate')
  private emitAgmDate (val: string): void { }

  /**
   * Emits an event with the new value of No AGM.
   */
  @Emit('noAGM')
  private emitNoAGM (val: boolean): void { }

  /**
   * Emits an event indicating whether or not this component is valid.
   */
  @Emit('valid')
  private emitValid (val: boolean): void { }
}

</script>

<style lang="stylus" scoped>
@import "../../assets/styles/theme.styl"

.validationErrorInfo
  color red

.value.date
  min-width 24rem

.meta-container
  display flex
  flex-flow column nowrap
  position relative

  > label:first-child
    font-weight 500

@media (min-width 768px)
  .meta-container
    flex-flow row nowrap

    > label:first-child
      flex 0 0 auto
      padding-right: 2rem
      width 12rem

#agm-checkbox
  font-size 14px
  margin-top 0
  margin-left -3px
  padding 0
</style>
