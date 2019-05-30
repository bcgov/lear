<template>
  <div id="annual-report">
    <v-container class="view-container">
      <article id="annual-report-article">
        <h1 id="AR-header">{{year}} Annual Report - <span style="font-style: italic">{{ reportState }}</span></h1>
        <div v-if="filedDate == null">
          <p>Review and certify your {{year}} Annual Report information.</p>
          <section>
            <h3 id="AR-step-1-header">1. Enter your Annual General Meeting Date</h3>
            <div id="AR-step-1-container">
              <AGMDate/>
            </div>
          </section>
          <section>
            <h3 id="AR-step-2-header">2. Registered Office Addresses</h3>
            <div id="AR-step-2-container">
              <RegisteredOfficeAddress/>
            </div>
          </section>
        </div>
        <div v-else>
          <ARComplete/>
        </div>
      </article>
      <aside>
        <affix relative-element-selector="#annual-report-article" :offset="{ top: 120, bottom: 40 }">
          <sbc-fee-summary v-bind:filingData="[...filingData]" />
        </affix>
      </aside>
    </v-container>
  </div>
</template>

<script>
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/ARSteps/RegisteredOfficeAddress.vue'
import ARComplete from '@/components/ARSteps/ARComplete.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'

export default {
  name: 'AnnualReport.vue',
  components: {
    AGMDate,
    RegisteredOfficeAddress,
    ARComplete,
    SbcFeeSummary,
    Affix
  },
  data () {
    return {
      filingData: []
    }
  },
  computed: {
    AGMDate () {
      return this.$store.state.AGMDate
    },
    noAGM () {
      return this.$store.state.noAGM
    },
    regOffAddrChange () {
      return this.$store.state.regOffAddrChange
    },
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
  mounted () {
  },
  methods: {
    toggleFiling (setting, filing) {
      var added = false
      for (var i = 0; i < this.filingData.length; i++) {
        if (this.filingData[i].filingTypeCode === filing) {
          if (setting === 'add') {
            added = true
            break
          } else {
            this.filingData.splice(i, 1)
            break
          }
        }
      }
      if (setting === 'add' && !added) {
        this.filingData.push({ filingTypeCode: filing, entityType: 'CP' })
      }
    }
  },
  watch: {
    AGMDate: function (val) {
      console.log('AnnualReport AGMDate watcher fired: ', val)
      if (val != null) {
        this.toggleFiling('add', 'OTANN')
      } else {
        if (!this.noAGM) this.toggleFiling('remove', 'OTANN')
      }
    },
    noAGM: function (val) {
      console.log('AnnualReport noAGM watcher fired: ', val)
      if (val) this.toggleFiling('add', 'OTANN')
      else this.toggleFiling('remove', 'OTANN')
    },
    regOffAddrChange: function (val) {
      console.log('AnnualReport regOffAddrChange watcher fired: ', val)
      if (val) this.toggleFiling('add', 'OTADD')
      else this.toggleFiling('remove', 'OTADD')
    },
    filingData: function (val) {
      console.log('AnnualReport filingData watcher fired: ', val)
    }
  }
}
</script>

<style lang="stylus">
  @import "../assets/styles/theme.styl"

  section
    header p
      color $gray6
      font-size 1rem

  .view-container
    display flex
    flex-flow column nowrap
    padding-top 3rem
    padding-bottom 3rem

  article
    flex 1 1 auto

  aside
    flex 0 0 auto
    width 20rem
    margin-top 3rem
    margin-right -8rem

    .affix
      width 20rem

  @media (min-width 960px)
    .view-container
      flex-flow row nowrap

      article
        margin-right 2rem

      aside
        margin-top 0
        width 20rem

  @media (max-width 768px)
    .view-container
      aside
        width 100%

        .affix
          position relative
          top 0 !important
          width 100%

  #annual-report
    width 100%

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
