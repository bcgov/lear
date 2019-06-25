<template>
  <div id="annual-report">

    <!-- Initial Page Load Transition -->
    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
        <div class="loading-msg">Preparing Your {{ year }} Annual Report</div>
      </div>
    </div>

    <v-container id="annual-report-container" class="view-container">
      <article id="annual-report-article" :class="this.agmDate ? 'agm-date-selected':'no-agm-date-selected'">
        <header>
          <h1 id="AR-header">File {{ year }} Annual Report -
            <span style="font-style: italic">{{ reportState }}</span>
          </h1>
          <p>Select your Annual General Meeting (AGM) date, and verify or change your Registered office address and List
            of Directors as of your AGM.</p>
        </header>

        <div v-if="filedDate == null">
          <!-- Annual General Meeting Date -->
          <section>
            <header>
              <h2 id="AR-step-1-header">1. Annual General Meeting Date</h2>
            </header>
            <v-card flat id="AR-step-1-container">
              <AGMDate ref="ARFilingDate" v-on:childToParent="onChildClick"/>
            </v-card>
          </section>

          <!-- Addresses -->
          <section>
            <header>
              <h2 id="AR-step-2-header">2. Registered Office Addresses
                <span class="agm-date">(as of {{ year }} Annual General Meeting)</span>
              </h2>
              <p>Verify or change your Registered Office Addresses.</p>
            </header>
            <v-card flat id="AR-step-2-container">
              <RegisteredOfficeAddress/>
            </v-card>
          </section>

          <!-- Director Information -->
          <section>
            <header>
              <h2 id="AR-step-3-header">3. Directors</h2>
              <p>Tell us who was elected or appointed and who ceased to be a director at your {{ year }} AGM.</p>
            </header>
            <!-- <v-card flat id="AR-step-3-container"> -->
              <Directors ref="directors" @directorsChange="directorsChangeEventHandler" />
            <!-- </v-card> -->
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

     <v-container id="submit-container" class="pt-0">
      <div class="ar-filing-buttons">
        <v-btn v-if="filedDate == null" id="ar-pay-btn" color="primary" large :disabled="!validated"
          @click="submit">File & Pay</v-btn>
        <v-btn v-else id="ar-next-btn" color="primary" large :disabled="currentYear == ARFilingYear"
          @click="nextAR">Next</v-btn>
        <v-btn id="ar-cancel-btn" large to="/Dashboard">Cancel</v-btn>
      </div>
    </v-container>

  </div>
</template>

<script>
import axios from '../axios-auth'
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/ARSteps/RegisteredOfficeAddress.vue'
import Directors from '@/components/ARSteps/Directors.vue'
import ARComplete from '@/components/ARSteps/ARComplete.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'

export default {
  name: 'AnnualReport.vue',
  components: {
    AGMDate,
    RegisteredOfficeAddress,
    Directors,
    ARComplete,
    SbcFeeSummary,
    Affix
  },
  data () {
    return {
      agmDate: '',
      directorsChange: false,
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
    validated () {
      return this.$store.state.validated
    },
    currentYear () {
      return this.$store.state.currentDate.substring(0, 4)
    },
    ARFilingYear () {
      return this.$store.state.ARFilingYear
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
    onChildClick (value) {
      this.agmDate = value
    },
    directorsChangeEventHandler (val) {
      this.directorsChange = val
    },
    getDirectors () {
      this.$refs.directors.getDirectors()
    },
    submit () {
      // todo: redirect to payment - will need to save state of page
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // probably need to parametrize date=this.$store.state.currentDate + add token in header for api
      var url = this.payURL
      var paymentJson
      // other team doing credit card entering/payment confirmation? - don't know what to check for in result
      axios.get(url).then(response => {
        paymentJson = response.data
        console.log('payment response: ', paymentJson)
        if (paymentJson) this.$store.state.filedDate = this.$store.state.currentDate
      }).catch(error => console.log('payment ERROR: ' + error))
      this.$store.state.filedDate = this.$store.state.currentDate
      console.log('submit: filedDate =', this.$store.state.filedDate)
    },
    resetARInfo () {
      this.$store.state.agmDate = null
      this.$store.state.filedDate = null
      this.$store.state.validated = false
      this.$store.state.noAGM = false
      this.$store.state.regOffAddrChange = false
      this.setRegOffAddrNull()
      this.$router.go()
    },
    nextAR () {
      this.resetARInfo()
      this.getARInfo(this.corpNum)
    },
    setRegOffAddrNull () {
      this.$store.state.DeliveryAddressStreet = null
      this.$store.state.DeliveryAddressStreetAdditional = null
      this.$store.state.DeliveryAddressCity = null
      this.$store.state.DeliveryAddressRegion = null
      this.$store.state.DeliveryAddressPostalCode = null
      this.$store.state.DeliveryAddressCountry = null
      this.$store.state.DeliveryAddressInstructions = null
      this.$store.state.MailingAddressStreet = null
      this.$store.state.MailingAddressStreetAdditional = null
      this.$store.state.MailingAddressCity = null
      this.$store.state.MailingAddressRegion = null
      this.$store.state.MailingAddressPostalCode = null
      this.$store.state.MailingAddressCountry = null
      this.$store.state.MailingAddressInstructions = null
    },
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
    directorsChange: function (val) {
      if (val) this.toggleFiling('add', 'OTCDR')
      else this.toggleFiling('remove', 'OTCDR')
    },
    filingData: function (val) {
      console.log('AnnualReport filingData watcher fired: ', val)
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  article
    .v-card
      line-height 1.2rem
      font-size 0.875rem

  section p
    //font-size 0.875rem
    color $gray6

  section + section
    margin-top 3rem

  h2
    margin-bottom 0.25rem

  #AR-header
    margin-bottom 1.25rem
    line-height 2rem
    letter-spacing -0.01rem
    font-size 2rem
    font-weight 500

  #AR-step-1-header, #AR-step-2-header, #AR-step-3-header
    margin-bottom 0.25rem
    margin-top 3rem
    font-size 1.125rem
    font-weight 500

  #AR-step-1-container, #AR-step-2-container, #AR-step-3-container
    margin-top 1rem

  .title-container
    margin-bottom 0.5rem

  .agm-date
    margin-left 0.25rem
    font-weight 300

  // Filing Buttons
  .ar-filing-buttons
    padding-top 2rem
    border-top: 1px solid $gray5
    text-align right
    .v-btn + .v-btn
      margin-left 0.5rem
</style>
