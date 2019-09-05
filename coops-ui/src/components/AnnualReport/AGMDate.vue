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
              :disabled="didNotHoldAGM"
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
          <!-- eslint-disable-next-line -->
          <span v-else-if="!$v.dateFormatted.isValidDay">
            Please enter a day between {{formatDate(minDate)}} and {{formatDate(maxDate)}}.
          </span>
        </div>
      </div>
    </div>

    <!-- don't show checkbox in current year -->
    <v-checkbox id="agm-checkbox"
                v-if="this.ARFilingYear && this.ARFilingYear < this.currentYear"
                v-model="didNotHoldAGM"
                :label=checkBoxLabel>
    </v-checkbox>
  </v-card>
</template>

<script>
import { isNotNull, isValidFormat, isValidYear, isValidMonth, isValidDay } from '@/validators'
import { mapState, mapActions, mapGetters } from 'vuex'
import DateUtils from '@/DateUtils'

export default {
  name: 'AGMDate',

  mixins: [DateUtils],

  props: { initialAgmDate: { type: String, default: '' } },

  data () {
    return {
      date: '', // bound to date picker
      dateFormatted: '', // bound to text field
      menu: false, // bound to calendar menu
      didNotHoldAGM: false, // bound to checkbox
      agmDateRules: [
        v => this.didNotHoldAGM || isNotNull(v) || 'An Annual General Meeting date is required.'
      ]
    }
  },

  validations () {
    return {
      dateFormatted: {
        isNotNull,
        isValidFormat,
        isValidYear,
        isValidMonth,
        isValidDay
      }
    }
  },

  computed: {
    ...mapState(['ARFilingYear', 'currentDate', 'lastPreLoadFilingDate']),

    ...mapGetters(['lastFilingDate']),

    checkBoxLabel () {
      return 'We did not hold an Annual General Meeting in ' + this.ARFilingYear
    },

    maxDate () {
      return (this.ARFilingYear === this.currentYear)
        ? this.currentDate.split('/').join('-')
        : `${this.ARFilingYear}-12-31`
    },

    minDate () {
      /**
       * Return the latest of the following dates:
       * - the first day of the AR filing year
       * - the last filing in filing history (from the Legal DB)
       * - the last pre-load Cobrs filing
       */
      const firstDayOfYear = +`${this.ARFilingYear}-01-01`.split('-').join('')
      const lastFilingDate = this.lastFilingDate ? +this.lastFilingDate.split('-').join('') : 0
      const lastPreLoadFilingDate = this.lastPreLoadFilingDate ? +this.lastPreLoadFilingDate.split('-').join('') : 0
      const minAgmDate = Math.max(firstDayOfYear, lastFilingDate, lastPreLoadFilingDate)
      return this.numToUsableString(minAgmDate)
    },

    currentYear () /* Number */ {
      return this.currentDate ? +this.currentDate.substring(0, 4) : null
    }
  },

  mounted () {
    // load initial data
    this.dateFormatted = this.formatDate(this.minDate)
  },

  methods: {
    formatDate (date) {
      // changes date from YYYY-MM-DD to YYYY/MM/DD
      if (!this.isValidDate(date, '-')) return ''
      const [year, month, day] = date.split('-')
      return `${year}/${month}/${day}`
    },

    parseDate (date) {
      // changes date from YYYY/MM/DD to YYYY-MM-DD
      if (!this.isValidDate(date, '/')) return ''
      const [year, month, day] = date.split('/')
      return `${year}-${month}-${day}`
    },

    isValidDate (date, separator) {
      return (isNotNull.call(this, date) &&
        isValidFormat.call(this, date, separator) &&
        isValidYear.call(this, date) &&
        isValidMonth.call(this, date) &&
        isValidDay.call(this, date))
    }
  },

  watch: {
    // when prop changes, load (initial) data
    initialAgmDate (val) {
      if (val) {
        this.dateFormatted = this.formatDate(val)
      } else {
        this.didNotHoldAGM = true
      }
    },

    // when text field changes, update date picker
    dateFormatted (val) {
      this.date = this.parseDate(val)
      // NB: let date watcher update parent
    },

    // when date picker changes, update text field etc
    date (val) {
      const agmDate = this.isValidDate(val, '-') ? val : null
      // only update text field if date is valid
      // this is to retain previous invalid values
      if (agmDate) {
        this.dateFormatted = this.formatDate(val)
      }
      this.$emit('agmDate', agmDate)
      this.$emit('valid', Boolean(this.didNotHoldAGM || agmDate))
    },

    // when checkbox changes, update text field etc
    didNotHoldAGM (val) {
      if (val) {
        // clear text field value
        this.dateFormatted = null
      } else {
        // reset text field value
        this.dateFormatted = this.formatDate(this.initialAgmDate || this.minDate)
      }
      this.$emit('noAGM', val)
      this.$emit('valid', Boolean(this.didNotHoldAGM || this.dateFormatted))
    }
  }
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
