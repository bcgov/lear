<template>
  <v-card flat class="cod-date-container">
    <div class="meta-container">
      <label>Director Change Date</label>

      <div class="value date">
        <v-menu
          ref="menu"
          v-model="menu"
          :nudge-right="40"
          transition="scale-transition"
          offset-y
          min-width="18rem">
          <template v-slot:activator="{ on }">
            <v-text-field
              id="cod-textfield"
              data-test-id="cod-date-text"
              v-model="dateFormatted"
              :rules="codDateRules"
              label="Enter your Director Change Date"
              hint="YYYY/MM/DD"
              append-icon="mdi-calendar"
              v-on="on"
              filled
            />
          </template>
          <v-date-picker
            id="cod-datepicker"
            data-test-id="cod-date-picker"
            v-model="date"
            :min=minDate
            :max=maxDate
            no-title
            @input="menu=true"
          />
        </v-menu>

        <div class="validationErrorInfo" v-if="$v.dateFormatted.isNotNull" data-test-id="cod-validation-error">
          <span v-if="!$v.dateFormatted.isValidFormat">
            Date must be in format YYYY/MM/DD.
          </span>
          <span v-else-if="!$v.dateFormatted.isValidCODDate">
            Please enter a month between {{formatDate(minDate)}} and {{formatDate(maxDate)}}.
          </span>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script lang="ts">
import { Component, Mixins, Vue, Prop, Watch, Emit } from 'vue-property-decorator'
import { isNotNull, isValidFormat, isValidCODDate } from '@/validators'
import { mapState, mapGetters } from 'vuex'
import DateMixin from '@/mixins/date-mixin'

@Component({
  mixins: [DateMixin],
  computed: {
    // Property definitions for runtime environment.
    ...mapState(['currentDate', 'lastAnnualReportDate', 'entityFoundingDate']),
    ...mapGetters(['lastCODFilingDate'])
  },
  validations: {
    dateFormatted: { isNotNull, isValidFormat, isValidCODDate }
  }
})
export default class CodDate extends Mixins(DateMixin) {
  // Prop passed into this component.
  @Prop({ default: '' })
  private initialCODDate: string

  // Local properties.
  private date: string = '' // bound to date picker
  private dateFormatted: string = '' // bound to text field
  private menu: boolean = false // bound to calendar menu

  // Local definitions of computed properties for static type checking.
  // Use non-null assertion operator to allow use before assignment.
  readonly currentDate!: string
  readonly lastAnnualReportDate!: string
  readonly lastCODFilingDate!: string
  readonly entityFoundingDate!: string

  /**
   * Computed value.
   * @returns The array of validations rules for the COD Date text field.
   */
  private get codDateRules (): Array<Function> {
    return [
      v => isNotNull(v) || 'A Director change date is required.'
    ]
  }

  /**
   * Computed value.
   * @returns The maximum date that can be entered.
   */
  private get maxDate (): string {
    return this.currentDate ? this.currentDate.split('/').join('-') : null
  }

  /**
   * Computed value.
   * @returns The minimum date that can be entered.
   */
  private get minDate (): string {
    /**
     * Determine the latest of the following dates:
     * - the last COD filing in filing history (from legal DB)
     * - the last AR filing in filing history (from the Legal DB)
     *
     * If the entity has no filing history, the founding date will be used.
     */
    let minDate = null
    if (!this.lastCODFilingDate && !this.lastAnnualReportDate) {
      minDate = this.entityFoundingDate.split('T')[0]
    } else {
      const lastARFilingDate = !this.lastAnnualReportDate ? 0 : +this.lastAnnualReportDate.split('-').join('')
      const lastCODFilingDate = !this.lastCODFilingDate ? 0 : +this.lastCODFilingDate.split('-').join('')
      const minCODDate = Math.max(lastARFilingDate, lastCODFilingDate)
      minDate = this.numToUsableString(minCODDate)
    }
    return minDate
  }

  /**
   * Called when component is mounted.
   */
  private mounted (): void {
    // load initial data
    this.dateFormatted = this.formatDate(this.initialCODDate)
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
      isValidCODDate.call(this, date, separator))
  }

  /**
   * When prop changes, load (initial) data.
   */
  @Watch('initialCODDate')
  private onInitialCODChanged (val: string): void {
    if (val) {
      this.dateFormatted = this.formatDate(val)
    }
  }

  /**
   * When text field changes, update date picker.
   */
  @Watch('dateFormatted')
  private onDateFormattedChanged (val: string): void {
    this.date = this.parseDate(val)
  }

  /**
   * When date picker changes, update text field etc.
   */
  @Watch('date')
  private onDateChanged (val: string): void {
    const codDate = this.isValidDate(val, '-') ? val : null
    // only update text field if date is valid
    // this is to retain previous invalid values
    if (codDate) {
      this.dateFormatted = this.formatDate(val)
    }
    this.emitCODDate(codDate)
    this.emitValid(Boolean(codDate))
  }

  /**
   * Emits an event with the new value of COD Date.
   */
  @Emit('codDate')
  private emitCODDate (val: string): void { }

  /**
   * Emits an event indicating whether or not this component is valid.
   */
  @Emit('valid')
  private emitValid (val: boolean): void { }
}
</script>

<style lang="scss" scoped>
// @import "@/assets/styles/theme.scss";

.cod-date-container {
  padding: 1.25rem;
}

.validationErrorInfo {
  color: red;
}

.value.date {
  min-width: 24rem;
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
</style>
