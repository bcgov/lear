<template>
  <div>
    <v-dialog  v-model="dialog" width="50rem">
      <v-card>
        <v-card-title>Error</v-card-title>

        <v-card-text>
          An error occured during processing. Please try later
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" flat @click="navigateToDashboard">
           Back to My Dashboard
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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

          <div v-if="isAnnualReportEditable">
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
                <RegisteredOfficeAddress ref="registeredAddress"/>
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
                <Directors @directorsChange="directorsChangeEventHandler" ref="directorsList"/>
              <!-- </v-card> -->
            </section>
          </div>
          <div v-else>
           <!-- <ARComplete/> -->
          </div>
        </article>

        <aside>
          <affix relative-element-selector="#annual-report-article" :offset="{ top: 120, bottom: 40 }">
            <sbc-fee-summary v-bind:filingData="[...filingData]" v-bind:payURL="payAPIURL"/>
          </affix>
        </aside>
      </v-container>

      <v-container id="submit-container" class="pt-0">
        <div class="ar-filing-buttons">
          <v-btn
            v-if="isAnnualReportEditable"
            id="ar-pay-btn"
            color="primary"
            large
            :disabled="!validated"
            @click="submit">
            File &amp; Pay
          </v-btn>
          <v-btn
            id="ar-cancel-btn"
            large
            to="/dashboard">
            Cancel
          </v-btn>
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
// import ARComplete from '@/components/AnnualReport/ARComplete.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapActions, mapGetters } from 'vuex'

export default {
  name: 'AnnualReport',

  components: {
    AGMDate,
    RegisteredOfficeAddress,
    Directors,
    // ARComplete,
    SbcFeeSummary,
    Affix
  },

  data () {
    return {
      showLoading: false,
      loadingMsg: 'Redirecting to PayBC to Process Your Payment',
      directorsChange: false,
      filingData: [],
      dialog: false
    }
  },

  computed: {
    ...mapState(['agmDate', 'noAGM', 'regOffAddrChange',
      'validated', 'currentDate', 'ARFilingYear', 'corpNum', 'lastAgmDate',
      'entityName', 'entityIncNo', 'entityFoundingDate', 'currentARStatus',
      'addressesFormValid', 'directorFormValid', 'agmDateValid']),

    ...mapGetters(['isAnnualReportEditable', 'reportState'])
  },

  mounted () {
    // if tombstone data isn't set, redirect to home
    if (!this.corpNum || !this.ARFilingYear) {
      this.$router.push('/')
    } else {
      // load initial data
      // TODO - anything here?
    }
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setValidated',
      'setAddressesFormValid', 'setDirectorFormValid', 'setAgmDateValid']),

    directorsChangeEventHandler (val) {
      this.directorsChange = val
    },

    submit () {
      let changeOfDirectors = null
      let changeOfAddress = null

      const header = {
        header: { name: 'annual_report', date: this.currentDate }
      }
      const business = {
        business: {
          foundingDate: this.entityFoundingDate,
          identifier: this.entityIncNo,
          legalName: this.entityName
        }
      }

      const annualReport = {
        annualReport: {
          annualGeneralMeetingDate: this.agmDate,
          certifiedBy: 'full name',
          email: 'no_one@never.get'
        }
      }

      if (this.isDataChanged('OTCDR')) {
        changeOfDirectors = {
          changeOfDirectors: {
            certifiedBy: 'Full Name',
            email: 'no_one@never.get',
            directors: this.$refs.directorsList.getAllDirectors()
          }
        }
      }

      if (this.isDataChanged('OTADD')) {
        changeOfAddress = {
          changeOfAddress: {
            certifiedBy: 'Full Name',
            email: 'no_one@never.get',
            deliveryAddress: this.$refs.registeredAddress.getDeliveryAddress(),
            mailingAddress: this.$refs.registeredAddress.getMailingAddress()
          }
        }
      }

      const filingData = {
        filing: Object.assign(
          {},
          header,
          business,
          annualReport,
          changeOfAddress,
          changeOfDirectors
        )
      }

      // Temp fix Added to remove cors error while invoking mock endpoint.
      // To be removed when the API is in place
      let config = {
        headers: {
          'Content-Type': 'text/plain'
        }
      }

      axios.post(this.corpNum + '/filings', filingData, config).then(res => {
        let payRequestId:String = res.data.filing.header.paymentToken
        payRequestId = '189'
        let returnURL = window.location.origin + '/AnnualReport?pay_id=' + payRequestId
        let authStub:string = this.authURL
        if (!(authStub.endsWith('/'))) {
          authStub = authStub + '/'
        }
        let payURL = authStub + 'makepayment/' + payRequestId + '/' + encodeURIComponent(returnURL)
        window.location.href = payURL
      }).catch((error) => {
        // TODO : To Decide how and where to display the error message from API
        console.log(error)
        this.dialog = true
      })
    },

    toggleFiling (setting, filing) {
      let added = false
      for (let i = 0; i < this.filingData.length; i++) {
        if (this.filingData[i].filingTypeCode === filing) {
          if (setting === 'add') {
            added = true
          } else {
            this.filingData.splice(i, 1)
          }
          break
        }
      }
      if (setting === 'add' && !added) {
        this.filingData.push({ filingTypeCode: filing, entityType: 'CP' })
      }
    },

    isDataChanged (key) {
      return this.filingData.find(o => o.filingTypeCode === key)
    },

    navigateToDashboard () {
      this.dialog = false
      this.$router.push('/')
    },

    setValidateFlag () {
      // compute the AR page's valid state
      this.setValidated(this.agmDateValid && this.addressesFormValid && this.directorFormValid)
    }
  },

  watch: {
    // TODO - what to do if Corp Num ever changes?
    // corpNum (val) {
    //   console.log('AnnualReport, corpNum =', val)
    // },

    agmDate (val) {
      // when AGM Date changes, update filing data
      console.log('AnnualReport, agmDate =', val)
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        if (!this.noAGM) this.toggleFiling('remove', 'OTANN')
      }
    },

    noAGM (val) {
      // when No AGM changes, update filing data
      console.log('AnnualReport, noAGM =', val)
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        this.toggleFiling('remove', 'OTANN')
      }
    },

    agmDateValid (val) {
      this.setValidateFlag()
    },

    regOffAddrChange: function (val) {
      // when addresses change, update filing data
      console.log('AnnualReport, regOffAddrChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTADD')
      } else {
        this.toggleFiling('remove', 'OTADD')
      }
    },

    addressesFormValid (val) {
      this.setValidateFlag()
    },

    directorsChange: function (val) {
      // when directors change, update filing data
      console.log('AnnualReport, directorsChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTCDR')
      } else {
        this.toggleFiling('remove', 'OTCDR')
      }
    },

    directorFormValid (val) {
      this.setValidateFlag()
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
@import '../assets/styles/theme.styl'

article
  .v-card
    line-height: 1.2rem;
    font-size: 0.875rem;

section p
  // font-size 0.875rem
  color: $gray6;

section + section
  margin-top: 3rem;

h2
  margin-bottom: 0.25rem;

#AR-header
  margin-bottom: 1.25rem;
  line-height: 2rem;
  letter-spacing: -0.01rem;
  font-size: 2rem;
  font-weight: 500;

#AR-step-1-header, #AR-step-2-header, #AR-step-3-header
  margin-bottom: 0.25rem;
  margin-top: 3rem;
  font-size: 1.125rem;
  font-weight: 500;

#AR-step-1-container, #AR-step-2-container, #AR-step-3-container
  margin-top: 1rem;

.title-container
  margin-bottom: 0.5rem;

.agm-date
  margin-left: 0.25rem;
  font-weight: 300;

// Filing Buttons
.ar-filing-buttons
  padding-top: 2rem;
  border-top: 1px solid $gray5;
  text-align: right;

  .v-btn + .v-btn
    margin-left: 0.5rem;
</style>
