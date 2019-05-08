<template>
<<<<<<< HEAD
  <v-container>
    <p>Filed {{filedDate}}</p>
    <div v-if="!noAGM">
      <h3>{{year}} Annual General Meeting Date</h3>
      <p>{{agmDate}}</p>
    </div>
    <div v-else>
      <h3>No Annual General Meeting Held</h3>
    </div>
  </v-container>
=======
  <p>You have completed all your Annual Reports</p>
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
</template>

<script>
export default {
<<<<<<< HEAD
  name: 'ARComplete.vue',
  computed: {
    filedDate () {
      console.log(this.$store.state.filedDate)
      var date = new Date(this.$store.state.filedDate + 'T12:00:00')
      return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    },
    year () {
      return this.$store.state.ARFilingYear
    },
    agmDate () {
      var date = new Date(this.$store.state.agmDate + 'T12:00:00')
      return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    },
    noAGM () {
      return this.$store.state.noAGM
    }
  }
=======
  name: 'ARComplete.vue'
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
}
</script>

<style scoped>

</style>
