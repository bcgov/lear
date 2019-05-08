<template>
  <div id="annual-report">
    <v-container>
      <div class="title-container">
        <h1 id="AR-header">{{year}} Annual Report - <span style="font-style: italic">{{ reportState }}</span>
        </h1>
<<<<<<< HEAD
        <div v-if="filedDate == null">
=======
        <div v-if="year != null">
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
          <p>Review and certify your {{year}} Annual Report information.</p>
          <h3 id="AR-step-1-header">1. Enter your Annual General Meeting Date</h3>
          <div id="AR-step-1-container">
            <AGMDate/>
          </div>
        </div>
        <div v-else>
          <ARComplete/>
        </div>
      </div>
    </v-container>
  </div>
</template>

<script>
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import ARComplete from '@/components/ARSteps/ARComplete.vue'

export default {
  name: 'AnnualReport.vue',
  components: {
    AGMDate,
    ARComplete
  },
  computed: {
<<<<<<< HEAD
    filedDate () {
      return this.$store.state.filedDate
    },
=======
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
    year () {
      return this.$store.state.ARFilingYear
    },
    reportState () {
<<<<<<< HEAD
      if (this.filedDate) return 'Filed'
      else return 'Draft'
=======
      if (this.year) return 'Draft'
      else return 'Filed'
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
    }
  },
  methods: {
  },
  watch: {
  }
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl";

  #AR-header
    display inline-block
    font-size 2rem
    font-weight 500

  #AR-step-1-header
    font-weight 500
    margin-top 3rem

  #AR-step-1-container
    margin-left 1.5rem
    margin-top 2rem

  .title-container
    margin-bottom 0.5rem

  p
    margin-top 1rem

</style>
