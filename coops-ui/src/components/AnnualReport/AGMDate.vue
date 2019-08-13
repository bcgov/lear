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

        <div class="validationErrorInfo">
          <span v-if="!$v.dateFormatted.isISOFormat">
            Date must be in format YYYY/MM/DD.
          </span>
          <span v-else-if="!$v.dateFormatted.isValidYear">
            Please enter a date within {{this.ARFilingYear}}.
          </span>
          <span v-else-if="$v.dateFormatted.isValidYear && !$v.dateFormatted.isValidMonth">
            Please enter a valid month in the past.
          </span>
          <!-- eslint-disable-next-line -->
          <span v-else-if="$v.dateFormatted.isValidYear && $v.dateFormatted.isValidMonth && !$v.dateFormatted.isValidDay">
            Please enter a valid day in the past.
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
import { isNotNull, isValidYear, isValidMonth, isValidDay, isISOFormat } from '@/validators'
import { mapState, mapActions, mapGetters } from 'vuex'
import DateUtils from '@/DateUtils'

export default {
  name: 'AGMDate',

  mixins: [DateUtils],

  data () {
    return {
      date: '', // bound to date picker
      dateFormatted: '', // bound to text field
      menu: false, // bound to calendar menu
      didNotHoldAGM: false, // bound to checkbox
      agmDateValid: true,
      agmDateRules: [
        v => this.didNotHoldAGM || isNotNull(v) || 'An Annual General Meeting date is required.'
      ]
    }
  },

  validations () {
    return {
      dateFormatted: {
        isISOFormat,
        isValidYear,
        isValidMonth,
        isValidDay
      }
    }
  },

  computed: {
    ...mapState(['ARFilingYear', 'agmDate', 'currentDate', 'lastPreLoadFilingDate']),

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
      /** return the latest of the following dates:
       *  - the most recent filing in filing history (from the Legal DB)
       *  - the last pre-load Cobrs filing
       *  - the first day of the AR year
       */
      // first day of filing year
      const firstDayOfYear = `${this.ARFilingYear}-01-01`.split('-').join('')

      // numeric versions of filing dates:
      const lastFilingDate = (this.lastFilingDate !== undefined && this.lastFilingDate !== null)
        ? this.lastFilingDate.split('-').join('') : 0
      const lastPreLoadFilingDate = (this.lastPreLoadFilingDate !== undefined && this.lastPreLoadFilingDate !== null)
        ? this.lastPreLoadFilingDate.split('-').join('') : 0
      const minAgmDate = Math.max(firstDayOfYear, lastFilingDate, lastPreLoadFilingDate)
      return this.numToUsableString(minAgmDate)
    },
    currentYear () /* Number */ {
      return this.currentDate ? +this.currentDate.substring(0, 4) : null
    }
  },

  mounted () {
    // load initial data
    this.setAgmDate(this.minDate)
    this.dateFormatted = this.formatDate(this.agmDate)
  },

  methods: {
    ...mapActions(['setAgmDate', 'setNoAGM', 'setAgmDateValid']),

    formatDate (date) {
      // changes date from YYYY-MM-DD to YYYY/MM/DD
      if (!this.isValidDateFormat(date, '-')) return ''
      const [year, month, day] = date.split('-')
      return `${year}/${month}/${day}`
    },
    parseDate (date) {
      // changes date from YYYY/MM/DD to YYYY-MM-DD
      if (!this.isValidDateFormat(date, '/')) return ''
      const [year, month, day] = date.split('/')
      return `${year}-${month}-${day}`
    },
    isValidDateFormat (date, separator) {
      // validates that date is:
      //    not empty or null
      //    in iso format
      //    is within the year of the ar
      //    the month is valid and in the past
      //    the day is valid and in the past
      // NB: use getUTCDate() to ignore local time (we only care about date part)
      return (date &&
        date.length === 10 &&
        date.indexOf(separator) === 4 &&
        date.indexOf(separator, 5) === 7 &&
        date.indexOf(separator, 8) === -1 &&
        +date.substring(0, 4) === this.ARFilingYear &&
        +date.substring(5, 7) > 0 &&
        +date.substring(5, 7) <= +this.maxDate.substring(5, 7) &&
        +date.substring(8, 10) === (new Date(date)).getUTCDate() &&
        +date.substring(8, 10) > 0 &&
        date.split(separator).join('') <= this.maxDate.split('-').join(''))
    },
    loadAgmDate (date) {
      // load data from existing filing
      if (!date) {
        this.didNotHoldAGM = true
      } else {
        this.dateFormatted = this.formatDate(date)
      }
    }
  },

  watch: {
    dateFormatted (val) {
      // when text field changes, update date picker
      this.date = this.parseDate(val)
    },
    date (val) {
      // when date picker changes, update text field and store
      if (this.didNotHoldAGM || val) {
        if (this.isValidDateFormat(val, '-')) {
          this.dateFormatted = this.formatDate(val)
        }
      }
      // also update value in store
      this.setAgmDate(val || null)
      this.setAgmDateValid(Boolean(this.didNotHoldAGM || this.agmDate))
    },
    didNotHoldAGM (val) {
      // when checkbox changes, update text field and store
      if (val) {
        this.setNoAGM(true)
        // clear text field value
        this.dateFormatted = null
      } else {
        this.setNoAGM(false)
        // reset text field value
        this.setAgmDate(this.minDate)
        this.dateFormatted = this.formatDate(this.agmDate)
      }
      this.setAgmDateValid(Boolean(this.didNotHoldAGM || this.agmDate))
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
