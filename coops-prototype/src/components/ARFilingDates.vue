<template>
  <ul class="director-list">
    <li class="container pb-2">
      <div class="meta-container">
        <label>
          <span>Annual General<br> Meeting Date</span>
        </label>
        <div class="value date">
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
                  min-width="290px">
                  <template v-slot:activator="{ on }">
                    <v-text-field
                      v-model="computedDateFormatted"
                      box
                      label="Select an Annual General Meeting Date"
                      append-icon="date_range"
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
            <!--
            <div class="form__row">
              <v-checkbox class="noAgm-checkbox" color="primary" label="No Annual General Meeting was held this year" v-model="noAgmDate"></v-checkbox>
            </div>
            -->
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
      v => !!v || 'An Annual General Meeting date is required'
    ]
  }),

  computed: {
    computedDateFormatted () {
      return this.date ? moment(this.date).format('MM/DD/YYYY') : ''
    }
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

  .value.date
    min-width 24rem

  .meta-container
    display flex
    flex-flow column nowrap
    position relative

    > label:first-child
      font-weight 500

    &__inner
      flex 1 1 auto

    .actions
      position absolute
      top 0
      right 0

      .v-btn
        min-width 4rem

      .v-btn + .v-btn
        margin-left 0.5rem

  @media (min-width 768px)
    .meta-container
      flex-flow row nowrap

      > label:first-child
        flex 0 0 auto
        padding-right: 2rem
        width 12rem

  .noAgm-checkbox
    margin-top 0
    margin-left -3px
    padding 0
</style>
