<template>
  <div>
    <!-- Transition to Payment -->
    <!-- TODO - this should be on Payment page -->
    <v-fade-transition>
      <div class="loading-container" v-show="showLoading">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">{{this.loadingMsg}}</div>
        </div>
      </div>
    </v-fade-transition>

    <div id="annual-report" ref="annualReport">
      <!-- Initial Page Load Transition -->
      <div class="loading-container fade-out">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">Preparing Your {{ ARFilingYear }} Annual Report</div>
        </div>
      </div>

      <v-container id="annual-report-container" class="view-container">
        <article id="annual-report-article" :class="this.agmDate ? 'agm-date-selected' : 'no-agm-date-selected'">
          <header>
            <h1 id="AR-header">File {{ ARFilingYear }} Annual Report -
              <span style="font-style: italic">{{ reportState }}</span>
            </h1>
            <p>Select your Annual General Meeting (AGM) date, and verify or change your Registered office address
              and List of Directors as of your AGM.</p>
          </header>

          <div v-if="filedDate === null">
            <!-- Annual General Meeting Date -->
            <section>
              <header>
                <h2 id="AR-step-1-header">1. Annual General Meeting Date</h2>
              </header>
              <v-card flat id="AR-step-1-container">
                <AGMDate/>
              </v-card>
            </section>

            <!-- Addresses -->
            <section>
              <header>
                <h2 id="AR-step-2-header">2. Registered Office Addresses
                  <span class="agm-date">(as of {{ ARFilingYear }} Annual General Meeting)</span>
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
                <p>Tell us who was elected or appointed and who ceased to be a director at your
                  {{ ARFilingYear }} AGM.</p>
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
          <v-btn v-if="filedDate === null" id="ar-pay-btn" color="primary" large :disabled="!validated"
            @click="submit">File & Pay</v-btn>
          <v-btn v-else id="ar-next-btn" color="primary" large :disabled="currentYear === ARFilingYear"
            @click="nextAR">Next</v-btn>
          <v-btn id="ar-cancel-btn" large to="/Dashboard">Cancel</v-btn>
        </div>
      </v-container>
    </div>
  </div>
</template>

<script lang="ts">
import axios from '@/axios-auth'
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/ARSteps/RegisteredOfficeAddress.vue'
import Directors from '@/components/ARSteps/Directors.vue'
import ARComplete from '@/components/ARSteps/ARComplete.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'

export default {
  name: 'AnnualReport',

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
      showLoading: false,
      loadingMsg: 'Redirecting to PayBC to Process Your Payment',
      directorsChange: false,
      filingData: []
    }
  },

  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
    currentDate () {
      return this.$store.state.currentDate
    },
    lastAgmDate () {
      return this.$store.state.lastAgmDate
    },
    ARFilingYear () {
      return this.$store.state.ARFilingYear
    },
    agmDate () {
      return this.$store.state.agmDate
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
      return this.currentDate ? this.currentDate.substring(0, 4) : null
    },
    reportState () {
      return this.filedDate ? 'Filed' : 'Draft'
    }
  },

  mounted () {
    // this logic works because Date() returns local time (plus offset which we ignore)
    const today = new Date()
    const year = today.getFullYear().toString()
    const month = (today.getMonth() + 1).toString().padStart(2, '0')
    const date = today.getDate().toString().padStart(2, '0')
    this.$store.state.currentDate = `${year}-${month}-${date}`
  },

  methods: {
    getLatestARInfo () {
      if (!this.corpNum) {
        console.log('getLatestARInfo() error - Corp Num is null')
      } else {
        // TODO - make proper axios call and delete hardcoded data below
        // TODO - when calling the api make sure this url is for most recent AR - stub specifies 2017
        var url = this.corpNum + '/filings?annual_report_year=2017'
        axios.get(url).then(response => {
          if (response && response.data) {
            this.setARInfo(response.data)
          } else {
            console.log('getLatestARInfo() error - invalid response data')
          }
        }).catch(error => {
          console.error('getLatestARInfo() error =', error)

          this.setARInfo({
            filing: {
              annual_report: {
                annual_general_meeting_date: '2017/05/10'
              }
            }
          })
        })
      }
    },
    getRegOffAddr () {
      if (!this.corpNum) {
        console.log('getRegOffAddr() error - Corp Num is null')
      } else {
        const url = this.corpNum
        axios.get(url).then(response => {
          if (response && response.data) {
            this.setRegOffAddr(response.data)
          } else {
            console.log('getRegOffAddr() error - invalid response data')
          }
        }).catch(error => console.error('getRegOffAddr() error =', error))
      }
    },
    setARInfo (lastARJson) {
      // assume JSON date is YYYY-MM-DD
      if (lastARJson && lastARJson.filing && lastARJson.filing.annual_report) {
        this.$store.state.lastAgmDate = lastARJson.filing.annual_report.annual_general_meeting_date
      } else {
        console.log('setARInfo() error - invalid Annual Report')
      }

      if (this.lastAgmDate && this.currentDate) {
        const lastAgmYear = +this.lastAgmDate.substring(0, 4)
        const currentYear = +this.currentDate.substring(0, 4)
        if (lastAgmYear === currentYear) {
          this.$store.state.ARFilingYear = null
        } else {
          this.$store.state.ARFilingYear = (lastAgmYear + 1).toString()
          // initial AGM date
          this.$store.state.agmDate = `${this.ARFilingYear}-01-01`
        }
      }
    },
    setRegOffAddr (regOffAddrJson) {
      if (regOffAddrJson && regOffAddrJson.business && regOffAddrJson.business.deliveryAddress) {
        const deliveryAddress = regOffAddrJson.business.deliveryAddress
        this.$store.state.DeliveryAddressStreet = deliveryAddress.streetAddress
        this.$store.state.DeliveryAddressStreetAdditional = deliveryAddress.streetAddressAdditional
        this.$store.state.DeliveryAddressCity = deliveryAddress.addressCity
        this.$store.state.DeliveryAddressRegion = deliveryAddress.addressRegion
        this.$store.state.DeliveryAddressPostalCode = deliveryAddress.postalCode
        this.$store.state.DeliveryAddressCountry = deliveryAddress.addressCountry
        this.$store.state.DeliveryAddressInstructions = deliveryAddress.deliveryInstructions
      } else {
        console.log('setRegOffAddr() error - invalid Delivery Address')
      }

      if (regOffAddrJson && regOffAddrJson.business && regOffAddrJson.business.mailingAddress) {
        const mailingAddress = regOffAddrJson.business.mailingAddress
        this.$store.state.MailingAddressStreet = mailingAddress.streetAddress
        this.$store.state.MailingAddressStreetAdditional = mailingAddress.streetAddressAdditional
        this.$store.state.MailingAddressCity = mailingAddress.addressCity
        this.$store.state.MailingAddressRegion = mailingAddress.addressRegion
        this.$store.state.MailingAddressPostalCode = mailingAddress.postalCode
        this.$store.state.MailingAddressCountry = mailingAddress.addressCountry
        this.$store.state.MailingAddressInstructions = mailingAddress.deliveryInstructions
      } else {
        console.log('setRegOffAddr() error - invalid Mailing Address')
      }
    },
    directorsChangeEventHandler (val) {
      this.directorsChange = val
    },
    submit () {
      // TODO - redirect to payment - will need to save state of page, etc
      // TODO - make proper axios call and delete hardcoded data below
      // TODO - other team doing credit card entering/payment confirmation? don't know what to check for in result
      // const url = this.payURL
      // axios.get(url).then(response => {
      //   if (response && response.data) {
      //     this.$store.state.filedDate = this.currentDate
      //   } else {
      //     console.log('submit() error - invalid response data')
      //   }
      // }).catch(error => console.error('submit() error =', error))

      this.$store.state.filedDate = this.currentDate
    },
    resetARInfo () {
      this.$store.state.agmDate = null
      this.$store.state.filedDate = null
      this.$store.state.validated = false
      this.$store.state.noAGM = false
      this.$store.state.regOffAddrChange = false
      this.setRegOffAddrNull()
      // refresh this page
      this.$router.go()
    },
    nextAR () {
      this.resetARInfo()
      this.getLatestARInfo()
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
    corpNum: function (val) {
      this.getLatestARInfo()
      this.getRegOffAddr()
      // TODO - Directors component should watch Corp Num and reload itself
      this.$refs.directors.getDirectors()
    },
    agmDate (val) {
      // when AGM Date changes, update filing data
      console.log('AnnualReport, agmDate =', val)
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        if (!this.noAGM) this.toggleFiling('remove', 'OTANN')
      }
      this.$store.state.validated = Boolean(this.noAGM || this.agmDate)
    },
    noAGM (val) {
      // when No AGM changes, update filing data
      console.log('AnnualReport, noAGM =', val)
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        this.toggleFiling('remove', 'OTANN')
      }
      this.$store.state.validated = Boolean(this.noAGM || this.agmDate)
    },
    regOffAddrChange: function (val) {
      console.log('AnnualReport, regOffAddrChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTADD')
      } else {
        this.toggleFiling('remove', 'OTADD')
      }
    },
    directorsChange: function (val) {
      console.log('AnnualReport, directorsChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTCDR')
      } else {
        this.toggleFiling('remove', 'OTCDR')
      }
    },
    validated (val) {
      console.log('AnnualReport, validated =', val)
    },
    filingData: function (val) {
      console.log('AnnualReport, filingData =', val)
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
