<template>
  <div id="agm-date" class="container">
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
  </div>
</template>

<script>
import { isNotNull, isValidYear, isValidMonth, isValidDay, isISOFormat } from '@/validators'

export default {
  name: 'AGMDate.vue',

  data () {
    return {
      date: '', // bound to date picker
      dateFormatted: '', // bound to text field
      menu: false, // bound to calendar menu
      didNotHoldAGM: false, // bound to checkbox
      agmDateValid: true,
      agmDateRules: [ v => this.didNotHoldAGM || isNotNull(v) || 'An Annual General Meeting date is required.' ]
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
    ARFilingYear () {
      return this.$store.state.ARFilingYear
    },
    checkBoxLabel () {
      return 'We did not hold an Annual General Meeting in ' + this.ARFilingYear
    },
    maxDate () {
      return (this.ARFilingYear === this.currentYear) ? this.currentDate : `${this.ARFilingYear}-12-31`
    },
    minDate () {
      return `${this.ARFilingYear}-01-01`
    },
    agmDate () {
      return this.$store.state.agmDate
    },
    currentDate () {
      return this.$store.state.currentDate
    },
    currentYear () {
      return this.currentDate ? this.currentDate.substring(0, 4) : null
    }
  },

  methods: {
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
        date.substring(0, 4) === this.ARFilingYear &&
        +date.substring(5, 7) > 0 &&
        +date.substring(5, 7) <= +this.maxDate.substring(5, 7) &&
        +date.substring(8, 10) === (new Date(date)).getUTCDate() &&
        +date.substring(8, 10) > 0 &&
        +date.substring(8, 10) <= +this.maxDate.substring(8, 10))
    }
  },

  watch: {
    dateFormatted (val) {
      // when text field changes, update date picker
      this.date = this.parseDate(val)
    },
    date (val) {
      // when date picker changes, update text field
      if (this.didNotHoldAGM || val) {
        if (this.isValidDateFormat(val, '-')) {
          this.dateFormatted = this.formatDate(val)
        }
      }
      // also update value in store
      this.$store.state.agmDate = val
    },
    didNotHoldAGM (val) {
      // when checkbox changes, update properties accordingly
      if (val) {
        this.$store.state.noAGM = true
        // clear text field value
        this.dateFormatted = null
      } else {
        this.$store.state.noAGM = false
        // reset text field value
        this.dateFormatted = ''
      }
    },
    ARFilingYear (val) {
      // when AR Filing Year changes (ie. on init), set initial text field value
      this.dateFormatted = this.formatDate(this.agmDate)
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

  .agm-checkbox
    font-size 14
    margin-top 0
    margin-left -3px
    padding 0
</style>
