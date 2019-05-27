<template>
  <ul class="director-list">
    <li class="container pb-2">
      <div class="meta-container">
        <label>
          <span>Annual General<br> Meeting Date</span>
        </label>
        <div class="value">
          <v-form v-model="agmDateValid">
            <v-expand-transition>
              <div class="form__row" v-show="!noAgmDate">
                  <v-menu
                    ref="menu1"
                    v-model="menu1"
                    :close-on-content-click="false"
                    :nudge-right="40"
                    lazy
                    transition="scale-transition"
                    offset-y
                    full-width
                    max-width="290px"
                    min-width="290px"
                  >
                    <template v-slot:activator="{ on }">
                      <v-text-field
                        v-model="computedDateFormatted"
                        box
                        label="Select an Annual General Meeting Date"
                        readonly
                        @blur="date = parseDate(dateFormatted)"
                        v-on="on"
                        :rules="agmDateRules"
                      ></v-text-field>
                    </template>
                    <v-date-picker v-model="date" no-title @input="menu1 = false" @click="$emit(this.date)"></v-date-picker>
                  </v-menu>
              </div>
            </v-expand-transition>
            <div class="form__row">
              <v-checkbox class="noAgm-checkbox" color="primary" label="No Annual General Meeting was held this year" v-model="noAgmDate"></v-checkbox>
            </div>
          </v-form>
        </div>
      </div>
    </li>
  </ul>
</template>

<script>
import moment from 'moment'

export default {
  name: 'ARFilingDates',

  props: {
    parentData: Object,
    stringProp: "Blah Blah blah",
    title: String
  },

  data: vm => ({
    noAgmDate: false,
    date: null,
    dateFormatted: null,
    menu1: false,
    menu2: false,

    agmDateValid: true,
    agmDateRules: [
      v => !!v || 'An Annual General Meeting date is required',
    ]
  }),

  computed: {
    computedDateFormatted () {
      return this.date ? moment(this.date).format('MM/DD/YYYY') : ''
      alert(computedDateFormatted)
    },
  },

  watch: {
    date (val) {
      this.dateFormatted = this.formatDate(this.date)
      this.$emit('childToParent', this.computedDateFormatted)
    }
  },

  methods: {
    emitToParent (event) {
      this.$emit('childToParent', this.dateFormatted)
    },

    formatDate (date) {
      if (!date) return null
      const [year, month, day] = date.split('-')
      return `${month}/${day}/${year}`
    },

    parseDate (date) {
      if (!date) return null
      const [month, day, year] = date.split('/')
      return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .noAgm-checkbox
    margin-top 0
    margin-left -3px
    padding 0

</style>