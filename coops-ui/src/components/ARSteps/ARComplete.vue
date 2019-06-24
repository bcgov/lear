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
export default {
  name: 'ARComplete.vue',
  computed: {
    filedDate () {
      console.log('ARComplete, filedDate =', this.$store.state.filedDate)
      var date = new Date(this.$store.state.filedDate + 'T12:00:00')
      return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    },
    ARFilingYear () {
      console.log('ARComplete, ARFilingYear =', this.$store.state.ARFilingYear)
      return this.$store.state.ARFilingYear
    },
    agmDate () {
      console.log('ARComplete, agmDate =', this.$store.state.agmDate)
      var date = new Date(this.$store.state.agmDate + 'T12:00:00')
      var dateString = date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
      return dateString
    },
    noAGM () {
      console.log('ARComplete, noAGM =', this.$store.state.noAGM)
      return this.$store.state.noAGM
    }
  }
}
</script>

<style scoped>
</style>
