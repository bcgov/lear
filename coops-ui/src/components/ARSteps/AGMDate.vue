<template>
  <div id="agm-date" class="container">
    <div class="meta-container">
      <label>
        <span>Annual General<br>Meeting Date</span>
      </label>

      <div class="value date">
        <v-form ref="agmDateForm" v-model="agmDateValid" @submit.prevent lazy-validation>
          <div v-show="!noAgmDate">
            <v-menu
              ref="menu"
              v-model="menu"
              :close-on-content-click="false"
              :nudge-right="40"
              :return-value.sync="date"
              lazy
              transition="scale-transition"
              offset-y
              max-width="290px"
              min-width="290px">
              <template v-slot:activator="{ on }">
                <div :class="{ 'validationError': $v.dateFormatted.$error }">
                  <v-text-field
                    v-model="dateFormatted"
                    label="Select or enter AGM Date"
                    hint="YYYY/MM/DD"
                    append-icon="event"
                    box
                    @blur="date = parseDate(dateFormatted)"
                    v-on="on"
                    :disabled="didNotHoldAGM"
                    :onchange="$v.dateFormatted.$touch()"
                    :rules="agmDateRules">
                  </v-text-field>
                </div>
              </template>
              <v-date-picker id="agm-datepicker"
                              v-model="date"
                              :min=minDate
                              :max=maxDate
                              no-title
                              scrollable>
                <v-btn flat color="primary" @click="$refs.menu.save(date)">OK</v-btn>
                <v-btn flat color="primary" @click="menu = false">CANCEL</v-btn>
              </v-date-picker>
            </v-menu>

            <div class="validationErrorInfo">
              <span v-if="!$v.dateFormatted.isISOFormat">
                Date must be in format YYYY/MM/DD.
              </span>
              <span v-if="!$v.dateFormatted.isValidYear">
                Please enter a date within {{this.ARFilingYear}}.
              </span>
              <span v-if="$v.dateFormatted.isValidYear && !$v.dateFormatted.isValidMonth">
                Please enter a valid month in the past.
              </span>
              <span v-if="$v.dateFormatted.isValidYear && $v.dateFormatted.isValidMonth
                && !$v.dateFormatted.isValidDay">
                Please enter a valid day in the past.
              </span>
            </div>
          </div>
        </v-form>
      </div>
    </div>

    <!-- only show checkbox after filing year -->
    <v-checkbox v-if="this.ARFilingYear < this.currentYear"
                id="agm-checkbox"
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
      dateFormatted: '', // bound to text field
      date: '', // bound to date picker
      menu: false, // bound to calendar menu
      didNotHoldAGM: false,
      noAgmDate: false,
      agmDateValid: true,
      agmDateRules: [ v => isNotNull(v) || 'An Annual General Meeting date is required.' ]
    }
  },

  computed: {
    currentYear () /* string */ {
      return this.$store.state.currentDate ? this.$store.state.currentDate.getFullYear().toString() : null
    },
    ARFilingYear () /* string */ {
      return this.$store.state.ARFilingYear
    },
    checkBoxLabel () {
      return 'We did not hold an Annual General Meeting in ' + this.ARFilingYear
    },
    maxDate () /* string */ {
      if (this.ARFilingYear === this.currentYear) {
        return this.$store.state.currentDate ? this.$store.state.currentDate.toISOString().substr(0, 10) : null
      } else {
        return `${this.ARFilingYear}-12-31`
      }
    },
    minDate () /* string */ {
      return `${this.ARFilingYear}-01-01`
    }
  },

  validations: function () {
    return {
      dateFormatted: {
        isISOFormat,
        isValidYear,
        isValidMonth,
        isValidDay
      }
    }
  },

  methods: {
    formatDate (date) {
      // changes date from YYYY-MM-DD to YYYY/MM/DD
      if (!this.isValidDate(date, '-')) return null

      const [year, month, day] = date.split('-')
      return `${year}/${month}/${day}`
    },
    parseDate (date) {
      // changes date from YYYY/MM/DD to YYYY-MM-DD
      if (!this.isValidDate(date, '/')) return null

      const [year, month, day] = date.split('/')
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
    },
    isValidDate (date, separator) {
      // TODO: can we use common validators here?
      // validates that date is:
      //    not undefined/null/empty
      //    in iso format
      //    is within the year of the ar
      //    the month is valid and in the past
      //    the day is valid and in the past
      if (!date) return false
      var day = (new Date(date)).getUTCDate()
      if (date.indexOf(separator) !== 4 ||
          date.indexOf(separator, 5) !== 7 ||
          date.indexOf(separator, 8) !== -1 ||
          date.length !== 10 ||
          date.substring(0, 4) !== this.ARFilingYear ||
          !(+date.substring(5, 7) !== 0 && +date.substring(5, 7) <= +this.maxDate.substring(5, 7)) ||
          !(+date.substring(8, 10) === day &&
            +date.substring(8, 10) !== 0 && +date.substring(8, 10) <= +this.maxDate.substring(8, 10))) {
        return false
      } else {
        return true
      }
    },
    validateAgmDateForm: function (index) {
      // TODO - delete this if we don't need it
      // if (this.$refs.agmDateForm.validate()) { }
    }
  },

  watch: {
    ARFilingYear: function (val) {
      // when AR Filing Year is set, set initial date picker value
      this.date = this.minDate
    },
    date (val) {
      // when date picker changed, update text field
      this.dateFormatted = this.formatDate(this.date)
      this.$store.state.validated = (this.dateFormatted !== null) || this.didNotHoldAGM
      this.$store.state.agmDate = new Date(this.dateFormatted)
    },
    agmDateValid: function (val) {
      // TODO - delete this if we don't need it
      // console.log('agmDateValid =', val)
    },
    // dateFormatted: function (val) {
    //   // when text field changes, update date picker
    //   console.log('dateFormatted =', val)
    //   if (this.isValidDate(val, '/')) {
    //     this.$store.state.validated = true
    //     this.date = this.parseDate(val)
    //   } else {
    //     this.$store.state.validated = false
    //   }
    // },
    // date: function (val) {
    //   if (!val) console.log('date is null')
    //   if (val) {
    //     // when date picker changes, update text field
    //     console.log('date =', val)
    //     // validate entered date
    //     if (!this.didNotHoldAGM && !val) {
    //       console.log('AGMDate valid = false')
    //       this.$store.state.validated = false
    //       this.$store.state.agmDate = null
    //     } else if (this.isValidDate(val, '-')) {
    //       console.log('AGMDate valid = true')
    //       this.$store.state.validated = true
    //       this.dateFormatted = this.formatDate(this.date)
    //       this.$store.state.agmDate = new Date(val)
    //     } else {
    //       console.log('else case')
    //     }
    //   }
    // },
    didNotHoldAGM: function (val) {
      // console.log('didNotHoldAGM =', val)
      if (val) {
        this.$store.state.validated = true
        this.$store.state.noAGM = true
      } else {
        this.$store.state.validated = false
        this.$store.state.noAGM = false
      }
      // reset text field to initial value (this also resets date picker)
      // this.dateFormatted = ''
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl";

  #agm-datepicker
    margin-bottom 0

  .validationError
    border-color red
    border-style groove
    border-width thin
    border-radius .3rem

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
