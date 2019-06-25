<template>
  <div id="agm-date">
    <v-container>
      <v-card>
        <v-flex id="agm-date-flex" xs10 sm4>
          <v-menu
            ref="agmDatePicker"
            v-model="agmDatePicker"
            :close-on-content-click="false"
            :nudge-right="100"
            lazy
            transition="scale-transition"
            offset-y
            full-width
            max-width="22rem"
            min-width="22rem">
            <template v-slot:activator="{ on }">
              <div :class="{'validationError': $v.dateFormatted.$error}">
                <v-text-field
                  class="agm-date-text-field"
                  :disabled="didNotHoldAGM"
                  v-model="dateFormatted"
                  :onchange="$v.dateFormatted.$touch()"
                  label="Annual General Meeting Date"
                  hint="YYYY/MM/DD"
                  persistent-hint
                  append-icon="event"
                  @blur="date = parseDate(dateFormatted)"
                  v-on="on">
                </v-text-field>
              </div>
            </template>
            <v-date-picker id="agm-datepicker"
                           v-model="date"
                           :min=minDate
                           :max=maxDate
                           color="blue"
                           no-title
                           @input="agmDatePicker = true">
              <v-btn flat color="blue" @click="$refs.agmDatePicker.save(date)">OK</v-btn>
              <v-btn flat color="blue" @click="agmDatePicker = false">Cancel</v-btn>
            </v-date-picker>
          </v-menu>
          <div class="validationErrorInfo">
            <span v-if="!$v.dateFormatted.isISOFormat">
              Date must be in format YYYY/MM/DD.
            </span>
            <span v-if="!$v.dateFormatted.isValidYear">
              Please enter a date within {{this.year}}.
            </span>
            <span v-if="$v.dateFormatted.isValidYear && !$v.dateFormatted.isValidMonth">
              Please enter a valid month in the past.
            </span>
            <span v-if="$v.dateFormatted.isValidYear && $v.dateFormatted.isValidMonth && !$v.dateFormatted.isValidDay">
              Please enter a valid day in the past.
            </span>
          </div>
        </v-flex>
        <v-checkbox v-if="this.year != this.currentDate.substring(0,4)"
                    id="agm-checkbox"
                    v-model="didNotHoldAGM"
                    :label=checkBoxLabel>
        </v-checkbox>
      </v-card>
    </v-container>
  </div>
</template>

<script>
import { isValidYear, isValidMonth, isValidDay, isISOFormat, test } from '../../../validators'

export default {
  name: 'AGMDate.vue',
  components: {},
  computed: {
    year () {
      return this.$store.state.ARFilingYear
    },
    checkBoxLabel () {
      return 'We did not hold an Annual General Meeting in ' + this.year
    },
    maxDate () {
      if (this.year === this.currentDate.substring(0, 4)) return this.currentDate
      return this.year + '-12-31'
    },
    minDate () {
      return this.year + '-01-01'
    },
    currentDate () {
      return this.$store.state.currentDate
    }
  },
  data () {
    return {
      date: '',
      dateFormatted: '',
      agmDatePicker: false,
      didNotHoldAGM: false
    }
  },
  validations: function () {
    var validations = {
      didNotHoldAGM: {
        test
      },
      dateFormatted: {
        isISOFormat,
        isValidYear,
        isValidMonth,
        isValidDay
      }
    }
    return validations
  },
  mounted () {
  },
  methods: {
    formatDate (date) {
      if (!date) return null
      if (!this.isValidDateFormat(date, '-')) return date

      const [year, month, day] = date.split('-')
      return `${year}/${month}/${day}`
    },
    parseDate (date) {
      if (!date) return null
      if (!this.isValidDateFormat(date, '/')) return null

      const [year, month, day] = date.split('/')
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
    },
    isValidDateFormat (date, separator) {
      // validates that date is:
      //    in isso format
      //    is within the year of the ar
      //    the month is valid and in the past
      //    the day is valid and in the past
      var day = (new Date(date)).getUTCDate()
      if (date !== null && date !== '' && (
        date.indexOf(separator) !== 4 ||
        date.indexOf(separator, 5) !== 7 ||
        date.indexOf(separator, 8) !== -1 ||
        date.length !== 10 ||
        date.substring(0, 4) !== this.year ||
        !(+date.substring(5, 7) !== 0 && +date.substring(5, 7) <= +this.maxDate.substring(5, 7)) ||
        !(+date.substring(8, 10) === day &&
          +date.substring(8, 10) !== 0 && +date.substring(8, 10) <= +this.maxDate.substring(8, 10))
      )) {
        return false
      } else {
        return true
      }
    }
  },
  watch: {
    dateFormatted: function (val) {
      console.log('AGMDate.vue dateFormatted watcher fired: ', val)
      this.date = this.parseDate(val)
    },
    date: function (val) {
      console.log('AGMDate.vue date watcher fired: ', val)
      // validate entered date
      if (!this.didNotHoldAGM && !val) {
        this.$store.state.validated = false
      } else if (this.isValidDateFormat(val, '-')) {
        this.$store.state.validated = true
        this.dateFormatted = this.formatDate(this.date)
      }
      this.$store.state.agmDate = val
    },
    didNotHoldAGM: function (val) {
      console.log('AGMDate.vue didNotHoldAGM watcher fired: ', val)
      if (val) {
        this.$store.state.validated = true
        this.$store.state.noAGM = true
      } else {
        this.$store.state.validated = false
        this.$store.state.noAGM = false
      }
      this.date = ''
    },
    year: function (val) {
      console.log('AGMDate year watcher fired: ', val)
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl";
  #agm-date-flex
    margin 0
    max-width 30rem

  #agm-datepicker
    margin-bottom 0

  .agm-date-text-field
    padding 1rem

  .validationError
    border-color red
    border-style groove
    border-width thin
    border-radius .3rem

  .validationErrorInfo
    color red

  .v-card
    padding 1rem

</style>
