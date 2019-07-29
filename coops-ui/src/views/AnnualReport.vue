<template>
  <div>
    <v-dialog v-model="dialog" width="50rem">
      <v-card>
        <v-card-title>Unable to Save Filing</v-card-title>
        <v-card-text>
          <p class="genErr">We were unable to save your filing. You can continue to try to save this
             filing or you can exit without saving and re-create this filing at another time.</p>
          <p  class="genErr">If you exit this filing, any changes you've made will not be saved.</p>
          <p class="genErr">
            <v-icon small>phone</v-icon>
            <a href="tel:+1-250-952-0568" class="error-dialog-padding">250 952-0568</a>
          </p>
          <p class="genErr">
            <v-icon small>email</v-icon>
            <a href="mailto:SBC_ITOperationsSupport@gov.bc.ca" class="error-dialog-padding"
              >SBC_ITOperationsSupport@gov.bc.ca</a>
          </p>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-btn color="primary" flat @click="navigateToDashboard">Exit without saving</v-btn>
          <v-spacer></v-spacer>
          <v-btn color="primary" flat @click="submit">Retry</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="paymentErrorDialog" width="60rem">
      <v-card>
        <v-card-title>Unable to Process Payment</v-card-title>
        <v-card-text>
          <p class="genErr">PayBC is unable to process payments at this time.</p>
          <p class="genErr">Your filing has been saved as a DRAFT and you can resume your filing from your Dashboard
            at a later time.</p>
          <p class="genErr">PayBC is normally available:</p>
          <p class="genErr">
            Monday to Friday: 6:00am to 9:00pm
            <br />Saturday: 12:00am to 7:00pm
            <br />Sunday: 12:00pm to 12:00am
          </p>
          <p class="genErr">
            <v-icon small>phone</v-icon>
            <a href="tel:+1-250-952-0568" class="error-dialog-padding">250 952-0568</a>
          </p>
          <p class="genErr">
            <v-icon small>email</v-icon>
            <a href="mailto:SBC_ITOperationsSupport@gov.bc.ca" class="error-dialog-padding"
              >SBC_ITOperationsSupport@gov.bc.ca</a>
          </p>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" flat @click="navigateToDashboard">Back to My Dashboard</v-btn>
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
                <RegisteredOfficeAddress
                  ref="registeredAddress"
                  :changeButtonDisabled="!agmDateValid"
                  :legalEntityNumber="corpNum"
                  @modified="officeModifiedEventHandler($event)"
                  @valid="officeValidEventHandler($event)"
                ></RegisteredOfficeAddress>
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

      <v-container id="buttons-container" class="list-item">
        <div class="buttons-left">
          <v-btn id="ar-save-btn" large
            v-if="isAnnualReportEditable"
            :disabled="true"><!-- !validated -->
            Save
          </v-btn>
          <v-btn id="ar-save-resume-btn" large
            v-if="isAnnualReportEditable"
            :disabled="true"><!-- !validated -->
            Save &amp; Resume Later
          </v-btn>
        </div>

        <div class="buttons-right">
          <v-tooltip bottom>
            <template v-slot:activator="{ on }">
              <v-btn
                v-if="isAnnualReportEditable"
                id="ar-pay-btn"
                color="primary"
                large
                :disabled="!validated"
                @click="submit"
                v-on="on">
                File &amp; Pay
              </v-btn>
            </template>
            <span>Ensure all of your information is entered correctly before you File &amp; Pay.<br>
              There is no opportunity to change information beyond this point.</span>
          </v-tooltip>
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
      dialog: false,
      paymentErrorDialog: false
    }
  },

  computed: {
    ...mapState(['agmDate', 'noAGM', 'regOffAddrChange',
      'validated', 'currentDate', 'ARFilingYear', 'corpNum', 'lastAgmDate',
      'entityName', 'entityIncNo', 'entityFoundingDate', 'currentARStatus',
      'addressesFormValid', 'directorFormValid', 'agmDateValid']),

    ...mapGetters(['isAnnualReportEditable', 'reportState'])
  },

  created () {
    // if tombstone data isn't set, redirect to home
    if (!this.corpNum || !this.ARFilingYear) {
      this.$router.push('/')
    } else if (this.id) {
      // load initial data
      this.fetchData()
    }
    // else do nothing (just load empty page)
    // this.filingData = []
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setRegOffAddrChange', 'setValidated',
      'setAddressesFormValid', 'setDirectorFormValid', 'setAgmDateValid']),

    fetchData () {
      // TODO: load draft Annual Report
      // in case of error, display popup
    },

    /**
     * Callback method for the "modified" event from RegisteredOfficeAddress.
     *
     * @param modified a boolean indicating whether or not the office address(es) have been modified from their
     * original values.
     */
    officeModifiedEventHandler (modified: boolean): void {
      console.log('AnnualReport, regOffAddrChange=', modified)

      // When addresses change, update the filing data.
      this.setRegOffAddrChange(modified)
      this.toggleFiling(modified ? 'add' : 'remove', 'OTADD')
    },

    /**
     * Callback method for the "valid" event from RegisteredOfficeAddress.
     *
     * @param valid a boolean that is true if the office addresses form contains valid data.
     */
    officeValidEventHandler (valid: boolean): void {
      this.setAddressesFormValid(valid)
      this.setValidateFlag()
    },

    directorsChangeEventHandler (val) {
      this.directorsChange = val
    },

    submit () {
      this.dialog = false
      let changeOfDirectors = null
      let changeOfAddress = null

      const header = {
        header: { name: 'annualReport', date: this.currentDate }
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

      axios.post(this.corpNum + '/filings', filingData).then(res => {
        let payRequestId: string = res.data.filing.header.paymentToken
        let returnURL = window.location.origin + '/AnnualReport?pay_id=' + payRequestId
        let authStub: string = this.authURL
        if (!(authStub.endsWith('/'))) {
          authStub = authStub + '/'
        }
        let payURL = authStub + 'makepayment/' + payRequestId + '/' + encodeURIComponent(returnURL)
        window.location.href = payURL
      }).catch((error) => {
        if (error.response && error.response.status && error.response.status === 402) {
          this.paymentErrorDialog = true
        } else {
          this.dialog = true
        }
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

// Save & Filing Buttons
#buttons-container
  padding-top: 2rem;
  border-top: 1px solid $gray5;

  .buttons-left
    width: 50%;

  .buttons-right
    margin-left auto

  .v-btn + .v-btn
    margin-left: 0.5rem;

.genErr
  font-size: 0.9rem;

.error-dialog-padding
  margin-left: 1rem;
</style>
