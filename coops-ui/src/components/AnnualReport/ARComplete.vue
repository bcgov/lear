<template>
  <v-container>
    <p>Filed {{filedDate}}</p>

    <div v-if="!noAGM">
      <h3>{{ARFilingYear}} Annual General Meeting Date</h3>
      <p>{{agmDate}}</p>
    </div>
    <div v-else>
      <h3>No Annual General Meeting Held</h3>
    </div>
  </v-container>
</template>

<script>
import { mapState } from 'vuex'
import DateUtils from '@/DateUtils'

export default {
  name: 'ARComplete',
  computed: {
    ...mapState(['ARFilingYear']),

    // dummy value for now
    // TODO: where to get Filed Date?
    filedDate () {
      const today = this.dateToUsableString(new Date())
      const date = new Date(today + 'T12:00:00')
      return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    },

    // dummy value for now
    // TODO: where to get AGM Date?
    agmDate () {
      return +`${this.ARFilingYear}-01-01`.split('-').join('')
    },

    // dummy value for now
    // TODO: where to get No AGM?
    noAGM () {
      return false
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"
</style>
