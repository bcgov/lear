<template>
  <div id="agm-date">
    <v-container>
      <v-flex xs10 sm4>
          <v-menu
            ref="agmDate"
            v-model="agmDate"
            :close-on-content-click="false"
            :nudge-right="25"
            lazy
            transition="scale-transition"
            offset-y
            full-width
            max-width="290px"
            min-width="290px">
            <template v-slot:activator="{ on }">
              <v-text-field
                :disabled="didNotHoldAGM"
                v-model="dateFormatted"
                label="Annual General Meeting Date"
                hint="YYYY/MM/DD"
                persistent-hint
                append-icon="event"
                @blur="date = parseDate(dateFormatted)"
                v-on="on">
              </v-text-field>
            </template>
            <v-date-picker id="agm-datepicker"
                           v-model="date"
                           :min=minDate
                           :max=maxDate
                           color="blue"
                           show-current="false"
                           no-title
                           @input="agmDate = true">
              <v-btn flat color="blue" @click="$refs.agmDate.save(date)">OK</v-btn>
              <v-btn flat color="blue" @click="agmDate = false">Cancel</v-btn>
            </v-date-picker>
          </v-menu>
      </v-flex>
      <v-checkbox v-if="this.year != this.currentDate.substring(0,4)"
                  id="agm-checkbox"
                  v-model="didNotHoldAGM"
                  :label=checkBoxLabel></v-checkbox>
    </v-container>
  </div>
</template>

<script>
import { agmDate, isISOFormat } from '../../../validators'

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
      return this.year + '12-31'
    },
    minDate () {
      if (this.didNotHoldAGM) return (+this.year + 1).toString() + '01-01'
      return this.year + '-01-01'
    }
  },
  data () {
    return {
      date: '',
      dateFormatted: '',
      currentDate: '',
      agmDate: false,
      didNotHoldAGM: false
    }
  },
  // validations: function () {
  //   var validations = {}
  //   if (this.year != null) {
  //     if (!this.didNotHoldAGM) {
  //       validations.date = {
  //         agmDate,
  //         isISOFormat
  //       }
  //     }
  //   }
  //   return validations
  // },
  mounted () {
    this.date = ''
    var today = new Date()
    this.currentDate = today.getFullYear() + '-' + ('0' + (+today.getMonth() + 1)).slice(-2) + '-' + ('0' + today.getDate()).slice(-2)
    console.log(this.currentDate)
  },
  methods: {
    formatDate (date) {
      if (!date) return null

      const [year, month, day] = date.split('-')
      return `${year}/${month}/${day}`
    },
    parseDate (date) {
      if (!date) return null

      const [year, month, day] = date.split('/')
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
    }
  },
  watch: {
    date: function (val) {
      console.log('AGMDate.vue date watcher fired: ', val)
      if (!this.didNotHoldAGM && (val === null || val === '')) {
        this.$store.state.validated = false
      } else {
        this.$store.state.validated = true
      }
      this.dateFormatted = this.formatDate(this.date)
    },
    didNotHoldAGM: function (val) {
      console.log('AGMDate.vue didNotHoldAGM watcher fired: ', val)
      if (val) this.$store.state.validated = true
      else this.$store.state.validated = false
      this.date = ''
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl";

  #agm-datepicker
    margin-bottom 0

</style>
