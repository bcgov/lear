<template>
  <div id="annual-report">
    <v-container>
      <div class="title-container">
        <h1 id="AR-header">{{year}} Annual Report - <span style="font-style: italic">{{ reportState }}</span></h1>
        <section>
          <div v-if="filedDate == null">
            <p>Review and certify your {{year}} Annual Report information.</p>
            <h3 id="AR-step-1-header">1. Enter your Annual General Meeting Date</h3>
            <div id="AR-step-1-container">
              <AGMDate/>
            </div>
            <h3 id="AR-step-2-header">2. Registered Office Addresses</h3>
            <div id="AR-step-2-container">
              <RegisteredOfficeAddress/>
            </div>
          </div>
          <div v-else>
            <ARComplete/>
          </div>
        </section>
      </div>
    </v-container>
  </div>
</template>

<script>
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/ARSteps/RegisteredOfficeAddress.vue'
import ARComplete from '@/components/ARSteps/ARComplete.vue'

export default {
  name: 'AnnualReport.vue',
  components: {
    AGMDate,
    RegisteredOfficeAddress,
    ARComplete
  },
  computed: {
    filedDate () {
      return this.$store.state.filedDate
    },
    year () {
      return this.$store.state.ARFilingYear
    },
    reportState () {
      if (this.filedDate) return 'Filed'
      else return 'Draft'
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
    margin-bottom 1.25rem
    line-height 2rem
    letter-spacing -0.01rem
    font-size 2rem
    font-weight 500

  #AR-step-1-header, #AR-step-2-header
    margin-bottom 0.25rem
    margin-top 3rem
    font-size 1.125rem
    font-weight 500

  #AR-step-1-container, #AR-step-2-container
    margin-left 1.5rem
    margin-top 2rem

  .title-container
    margin-bottom 0.5rem

  p
    margin-top 1rem

</style>
