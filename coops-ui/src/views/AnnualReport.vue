<template>
  <div>
    <v-dialog v-model="resumeErrorDialog" width="50rem" persistent>
      <v-card>
        <v-card-title>Unable to Resume Filing</v-card-title>
        <v-card-text>
          <p class="genErr">We were unable to resume your filing. You can return to your dashboard
            and try again.</p>
          <p class="genErr">If this error persists, please contact us.</p>
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
          <v-btn color="primary" flat @click="navigateToDashboard">Return to dashboard</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="saveErrorDialog" width="50rem">
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
          <v-btn color="primary" flat @click="onClickFilePay" :disabled="filingPaying">Retry</v-btn>
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

    <div id="annual-report">
      <!-- Initial Page Load Transition -->
      <div class="loading-container fade-out">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">{{this.loadingMessage}}</div>
        </div>
      </div>

      <v-container id="annual-report-container" class="view-container">
        <article id="annual-report-article" :class="this.agmDate ? 'agm-date-selected' : 'no-agm-date-selected'">
          <header>
            <h1 id="AR-header">File {{ ARFilingYear }} Annual Report
              <span style="font-style: italic" v-if="reportState">- {{ reportState }}</span>
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
              <AGMDate ref="agmDate" />
            </section>

            <!-- Registered Office Addresses -->
            <section>
              <header>
                <h2 id="AR-step-2-header">2. Registered Office Addresses
                  <span class="agm-date">(as of {{ ARFilingYear }} Annual General Meeting)</span>
                </h2>
                <p>Verify or change your Registered Office Addresses.</p>
              </header>
              <RegisteredOfficeAddress
                :changeButtonDisabled="!agmDateValid"
                :legalEntityNumber="corpNum"
                :addresses.sync="addresses"
                @modified="officeModifiedEventHandler($event)"
                @valid="officeValidEventHandler($event)" />
            </section>

            <!-- Directors -->
            <section>
              <header>
                <h2 id="AR-step-3-header">3. Directors</h2>
                <p>Tell us who was elected or appointed and who ceased to be a director at your
                  {{ ARFilingYear }} AGM.</p>
              </header>
              <Directors ref="directorsList"
                @directorsChange="directorsChange"
                :asOfDate="agmDate"
                :componentEnabled="agmDateValid"
              />
            </section>

            <!-- Certify -->
            <section>
              <header>
                <h2 id="AR-step-4-header">4. Certify Correct</h2>
                <p>Enter the name of the current director, officer, or lawyer submitting this Annual Report.</p>
              </header>
              <Certify @certifyChange="changeCertifyData" @certifiedBy="certifiedBy=$event" ref="certifyClause"/>
            </section>
          </div>
          <!-- <div v-else>
            <ARComplete/>
          </div> -->
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
            :disabled="!isSaveButtonEnabled || saving"
            :loading="saving"
            @click="onClickSave">
            Save
          </v-btn>
          <v-btn id="ar-save-resume-btn" large
            v-if="isAnnualReportEditable"
            :disabled="!isSaveButtonEnabled || savingResuming"
            :loading="savingResuming"
            @click="onClickSaveResume">
            Save &amp; Resume Later
          </v-btn>
        </div>

        <div class="buttons-right">
          <v-tooltip bottom>
            <v-btn
              slot="activator"
              v-if="isAnnualReportEditable"
              id="ar-file-pay-btn"
              color="primary"
              large
              :disabled="!validated || filingPaying"
              :loading="filingPaying"
              @click="onClickFilePay">
              File &amp; Pay
            </v-btn>
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
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapActions, mapGetters } from 'vuex'
import { PAYMENT_REQUIRED } from 'http-status-codes'
import Certify from '@/components/AnnualReport/Certify.vue'

export default {
  name: 'AnnualReport',

  components: {
    AGMDate,
    RegisteredOfficeAddress,
    Directors,
    SbcFeeSummary,
    Affix,
    Certify
  },

  data () {
    return {
      addresses: null,
      filingId: null,
      loadingMessage: 'Loading...', // initial generic message
      filingData: [],
      resumeErrorDialog: false,
      saveErrorDialog: false,
      paymentErrorDialog: false,
      certifyChange: false,
      certifiedBy: null,
      isSaveButtonEnabled: false,
      saving: false,
      savingResuming: false,
      filingPaying: false
    }
  },

  computed: {
    ...mapState(['agmDate', 'noAGM', 'regOffAddrChange',
      'validated', 'currentDate', 'ARFilingYear', 'corpNum', 'lastAgmDate',
      'entityName', 'entityIncNo', 'entityFoundingDate', 'currentFilingStatus',
      'addressesFormValid', 'directorFormValid', 'agmDateValid']),

    ...mapGetters(['isAnnualReportEditable', 'reportState'])
  },

  created () {
    // NB: filing id of 0 means "new AR"
    // otherwise it's a draft AR filing id
    this.filingId = this.$route.params.id

    // if tombstone data isn't set, route to home
    if (!this.corpNum || !this.ARFilingYear || (this.filingId === undefined)) {
      this.$router.push('/')
    } else if (this.filingId > '0') {
      // resume draft filing
      this.loadingMessage = `Resuming Your ${this.ARFilingYear} Annual Report`
      this.fetchData()
    } else {
      // else just load new page
      this.loadingMessage = `Preparing Your ${this.ARFilingYear} Annual Report`
    }
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setRegOffAddrChange', 'setValidated',
      'setAddressesFormValid', 'setDirectorFormValid', 'setAgmDateValid']),

    fetchData () {
      const url = this.corpNum + '/filings/' + this.filingId
      axios.get(url).then(response => {
        if (response && response.data) {
          const filing = response.data.filing
          try {
            // verify data
            if (!filing) throw new Error('missing filing')
            if (!filing.header) throw new Error('missing header')
            if (!filing.business) throw new Error('missing business')
            if (filing.header.name !== 'annualReport') throw new Error('invalid filing type')
            if (filing.header.status !== 'DRAFT') throw new Error('invalid filing status')
            if (filing.business.identifier !== this.entityIncNo) throw new Error('invalid business identifier')
            if (filing.business.legalName !== this.entityName) throw new Error('invalid business legal name')

            // load Annual Report fields
            if (!filing.annualReport) throw new Error('missing annual report')
            else {
              // TODO: use props instead of $refs (which cause an error in the unit tests)
              // NOTE: AR Filing Year (which is needed by agmDate component) was already set by Todo List
              this.$refs.directorsList.setDraftDate(filing.annualReport.annualGeneralMeetingDate)
              this.$refs.agmDate.loadAgmDate(filing.annualReport.annualGeneralMeetingDate)
              this.toggleFiling('add', 'OTANN')
            }

            // load Change of Directors fields
            const changeOfDirectors = filing.changeOfDirectors
            if (changeOfDirectors) {
              if (changeOfDirectors.directors && changeOfDirectors.directors.length > 0) {
                this.$refs.directorsList.setAllDirectors(changeOfDirectors.directors)
                this.toggleFiling('add', 'OTCDR')
              } else {
                throw new Error('invalid change of directors')
              }
            } else {
              // To handle the condition of save as draft withouot change of director
              this.$refs.directorsList.getDirectors()
            }

            // load Change of Address fields
            const changeOfAddress = filing.changeOfAddress
            if (changeOfAddress) {
              if (changeOfAddress.deliveryAddress && changeOfAddress.mailingAddress) {
                this.addresses = {
                  deliveryAddress: changeOfAddress.deliveryAddress,
                  mailingAddress: changeOfAddress.mailingAddress
                }
                this.toggleFiling('add', 'OTADD')
              } else {
                throw new Error('invalid change of address')
              }
            }
          } catch (err) {
            console.log(`fetchData() error - ${err.message}, filing =`, filing)
            this.resumeErrorDialog = true
          }
        } else {
          console.log('fetchData() error - invalid response =', response)
          this.resumeErrorDialog = true
        }
      }).catch(error => {
        console.error('fetchData() error =', error)
        this.resumeErrorDialog = true
      })
    },

    /**
     * Callback method for the "modified" event from RegisteredOfficeAddress.
     *
     * @param modified a boolean indicating whether or not the office address(es) have been modified from their
     * original values.
     */
    officeModifiedEventHandler (modified: boolean): void {
      // when addresses change, update filing data
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

    directorsChange (val) {
      // when directors change, update filing data
      if (val) {
        this.toggleFiling('add', 'OTCDR')
      } else {
        this.toggleFiling('remove', 'OTCDR')
      }
    },

    changeCertifyData (val) {
      this.certifyChange = val
    },

    async onClickSave () {
      this.saving = true
      const filing = await this.saveFiling(true)
      if (!filing) {
        console.log('onClickSave() error - invalid filing =', filing)
      } else {
        this.filingId = filing.header.filingId
      }
      this.saving = false
    },

    async onClickSaveResume () {
      this.savingResuming = true
      const filing = await this.saveFiling(true)
      // on success, route to Home URL
      if (filing) {
        this.$router.push('/')
      } else {
        console.log('onClickSaveResume() error - invalid filing =', filing)
      }
      this.savingResuming = false
    },

    async onClickFilePay () {
      this.filingPaying = true
      const filing = await this.saveFiling(false)
      // on success, redirect to Pay URL
      if (filing && filing.header) {
        const origin = window.location.origin || ''
        const filingId = filing.header.filingId
        const returnURL = encodeURIComponent(origin + '/Dashboard?filing_id=' + filingId)
        let authStub: string = this.authURL || ''
        if (!(authStub.endsWith('/'))) { authStub += '/' }
        const paymentToken = filing.header.paymentToken
        const payURL = authStub + 'makepayment/' + paymentToken + '/' + returnURL
        // assume Pay URL is always reachable
        window.location.assign(payURL)
      } else {
        console.log('onClickFilePay() error - invalid filing =', filing)
      }
      this.filingPaying = false
    },

    async saveFiling (isDraft) {
      this.saveErrorDialog = false
      let changeOfDirectors = null
      let changeOfAddress = null

      const header = {
        header: {
          name: 'annualReport',
          date: this.currentDate
        }
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
          certifiedBy: this.certifiedBy || '',
          email: 'no_one@never.get'
        }
      }

      if (this.isDataChanged('OTCDR')) {
        changeOfDirectors = {
          changeOfDirectors: {
            certifiedBy: this.certifiedBy || '',
            email: 'no_one@never.get',
            directors: this.$refs.directorsList.getAllDirectors()
          }
        }
      }

      if (this.isDataChanged('OTADD') && this.addresses) {
        changeOfAddress = {
          changeOfAddress: {
            certifiedBy: this.certifiedBy || '',
            email: 'no_one@never.get',
            deliveryAddress: this.addresses['deliveryAddress'],
            mailingAddress: this.addresses['mailingAddress']
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

      if (this.filingId > '0') {
        // we have a filing id, so we are updating an existing filing
        let url = this.corpNum + '/filings/' + this.filingId
        if (isDraft) { url += '?draft=true' }
        let filing = null
        await axios.put(url, filingData).then(res => {
          if (!res || !res.data || !res.data.filing) { throw new Error('invalid API response') }
          filing = res.data.filing
        }).catch(error => {
          console.error('saveFiling() error =', error)
          if (error && error.response && error.response.status === PAYMENT_REQUIRED) {
            this.paymentErrorDialog = true
          } else {
            this.saveErrorDialog = true
          }
        })
        return filing
      } else {
        // filing id is '0', so we are saving a new filing
        let url = this.corpNum + '/filings'
        if (isDraft) { url += '?draft=true' }
        let filing = null
        await axios.post(url, filingData).then(res => {
          if (!res || !res.data || !res.data.filing) { throw new Error('invalid API response') }
          filing = res.data.filing
        }).catch(error => {
          console.error('saveFiling() error =', error)
          if (error && error.response && error.response.status === PAYMENT_REQUIRED) {
            this.paymentErrorDialog = true
          } else {
            this.saveErrorDialog = true
          }
        })
        return filing
      }
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
      this.$router.push('/dashboard')
    },

    setValidateFlag () {
      // compute the AR page's valid state
      this.setValidated(this.agmDateValid && this.addressesFormValid && this.directorFormValid && this.certifyChange)
      this.isSaveButtonEnabled = this.agmDateValid && this.addressesFormValid && this.directorFormValid
    }
  },

  watch: {
    agmDate (val) {
      // when AGM Date changes, update filing data
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        if (!this.noAGM) this.toggleFiling('remove', 'OTANN')
      }
    },

    noAGM (val) {
      // when No AGM changes, update filing data
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        this.toggleFiling('remove', 'OTANN')
      }
    },

    agmDateValid (val) {
      this.setValidateFlag()
    },

    directorFormValid (val) {
      this.setValidateFlag()
    },

    certifyChange: function (val) {
      this.setValidateFlag()
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

#AR-step-1-header, #AR-step-2-header, #AR-step-3-header, #AR-step-4-header
  margin-bottom: 0.25rem;
  margin-top: 3rem;
  font-size: 1.125rem;
  font-weight: 500;

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
