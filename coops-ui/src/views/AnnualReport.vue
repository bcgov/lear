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
          <v-btn id="ar-cancel-btn" large to="/dashboard">Cancel</v-btn>
        </div>
      </v-container>
    </div>
  </div>
</template>

<script lang="ts">
import axios from '@/axios-auth'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import ARComplete from '@/components/AnnualReport/ARComplete.vue'
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
      // TODO - look at filing.annual.status instead
      return this.filedDate ? 'Filed' : 'Draft'
    }
  },

  mounted () {
    console.log('AnnualReport is mounted')
    console.log('AnnualReport, corpNum =', this.corpNum)
    console.log('AnnualReport, ARFilingYear =', this.ARFilingYear)
    // if tombstone data isn't set, go back to home
    if (!this.corpNum || !this.ARFilingYear) {
      this.$router.push('/')
    } else {
      // load initial data
      // TODO - need to get id of latest AR
      this.getARInfo(1)
      this.getRegOffAddr()
      // TODO - Directors component should watch Corp Num and reload itself
      this.$refs.directors.getDirectors()
    }
  },

  methods: {
    getARInfo (id) {
      if (this.corpNum) {
        // TODO - make proper axios call
        var url = this.corpNum + '/filings/' + id
        axios.get(url).then(response => {
          if (response && response.data) {
            this.setARInfo(response.data)
          } else {
            console.log('getARInfo() error - invalid response data')
          }
        }).catch(error => {
          console.error('getARInfo() error =', error)

          // TODO - delete this when API works
          this.setARInfo({})
        })
      }
    },
    getRegOffAddr () {
      if (this.corpNum) {
        const url = this.corpNum + '/addresses'
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
      if (lastARJson && lastARJson.filing && lastARJson.filing.annualReport) {
        // TODO - do something with this data
      } else {
        console.log('setARInfo() error - invalid Annual Report')
      }
      // if (this.lastAgmDate && this.currentDate) {
      //   const lastAgmYear = +this.lastAgmDate.substring(0, 4)
      //   const currentYear = +this.currentDate.substring(0, 4)
      //   if (lastAgmYear === currentYear) {
      //     // entity has already filed
      //     alert('Error: annual report for this year has already been filed.')
      //     // go back to home
      //     this.$router.push('/')
      //   } else {
      //     this.$store.state.ARFilingYear = (lastAgmYear + 1).toString()
      //     // initial AGM date
      //     this.$store.state.agmDate = `${this.ARFilingYear}-01-01`
      //   }
      // } else {
      //   console.log('setARInfo() error - invalid Last AGM Date or Current Date')
      //   // go back to home
      //   this.$router.push('/')
      // }
    },
    setRegOffAddr (regOffAddrJson) {
      if (regOffAddrJson && regOffAddrJson.deliveryAddress) {
        this.$store.state.DeliveryAddressStreet = regOffAddrJson.deliveryAddress.streetAddress
        this.$store.state.DeliveryAddressStreetAdditional = regOffAddrJson.deliveryAddress.streetAddressAdditional
        this.$store.state.DeliveryAddressCity = regOffAddrJson.deliveryAddress.addressCity
        this.$store.state.DeliveryAddressRegion = regOffAddrJson.deliveryAddress.addressRegion
        this.$store.state.DeliveryAddressPostalCode = regOffAddrJson.deliveryAddress.postalCode
        this.$store.state.DeliveryAddressCountry = regOffAddrJson.deliveryAddress.addressCountry
        this.$store.state.DeliveryAddressInstructions = regOffAddrJson.deliveryAddress.deliveryInstructions
      } else {
        console.log('setRegOffAddr() error - invalid Delivery Address')
      }

      if (regOffAddrJson && regOffAddrJson.mailingAddress) {
        this.$store.state.MailingAddressStreet = regOffAddrJson.mailingAddress.streetAddress
        this.$store.state.MailingAddressStreetAdditional = regOffAddrJson.mailingAddress.streetAddressAdditional
        this.$store.state.MailingAddressCity = regOffAddrJson.mailingAddress.addressCity
        this.$store.state.MailingAddressRegion = regOffAddrJson.mailingAddress.addressRegion
        this.$store.state.MailingAddressPostalCode = regOffAddrJson.mailingAddress.postalCode
        this.$store.state.MailingAddressCountry = regOffAddrJson.mailingAddress.addressCountry
        this.$store.state.MailingAddressInstructions = regOffAddrJson.mailingAddress.deliveryInstructions
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
      // TODO - need to get id of next AR
      this.getARInfo()
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
    // TODO - what to do if Corp Num ever changes?
    // corpNum (val) {
    //   console.log('AnnualReport - got corpNum =', val)
    // },
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
