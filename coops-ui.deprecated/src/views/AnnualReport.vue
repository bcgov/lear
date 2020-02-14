<template>
  <div id="annual-report">
    <confirm-dialog
      ref="confirm"
      attach="#annual-report"
    />

    <resume-error-dialog
      :dialog="resumeErrorDialog"
      @exit="navigateToDashboard"
      attach="#annual-report"
    />

    <save-error-dialog
      filing="Annual Report"
      :dialog="saveErrorDialog"
      :disableRetry="busySaving"
      :errors="saveErrors"
      :warnings="saveWarnings"
      @exit="navigateToDashboard"
      @retry="onClickFilePay"
      @okay="resetErrors"
      attach="#annual-report"
    />

    <payment-error-dialog
      :dialog="paymentErrorDialog"
      @exit="navigateToDashboard"
      attach="#annual-report"
    />

    <!-- Initial Page Load Transition -->
    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
        <div class="loading-msg">{{loadingMessage}}</div>
      </div>
    </div>

    <v-container id="annual-report-container" class="view-container">
      <v-row>
        <v-col cols="12" lg="9">
          <section>
            <!-- COOP only: -->
            <article
              class="annual-report-article"
              :class="agmDate ? 'agm-date-selected' : 'no-agm-date-selected'"
              v-if="entityFilter(EntityTypes.COOP)"
            >
              <!-- Page Title -->
              <header>
                <h1 id="AR-header">File {{ARFilingYear}} Annual Report
                  <span class="font-italic" v-if="reportState"> &mdash; {{reportState}}</span>
                </h1>
                <p>Please verify or change your Office Addresses and Directors.</p>
              </header>

              <template v-if="isAnnualReportEditable">
                <!-- Annual General Meeting Date -->
                <section>
                  <header>
                    <h2 id="AR-step-1-header">1. Annual General Meeting Date</h2>
                    <p>Select your Annual General Meeting (AGM) date.</p>
                  </header>
                  <agm-date
                    :newAgmDate="newAgmDate"
                    :newNoAgm="newNoAgm"
                    :allowCOA="allowChange('coa')"
                    :allowCOD="allowChange('cod')"
                    @agmDate="onAgmDateChange($event)"
                    @noAgm="onNoAgmChange($event)"
                    @valid="onAgmDateValidChange($event)"
                  />
                </section>

                <!-- Registered Office Addresses -->
                <section v-show="agmDate || noAgm">
                  <header>
                    <h2 id="AR-step-2-header">2. Registered Office Addresses
                      <span class="as-of-date" v-if="agmDate">(as of {{ARFilingYear}} Annual General Meeting)</span>
                      <span class="as-of-date" v-else>(as of {{asOfDate}})</span>
                    </h2>
                    <p>Verify or change your Registered Office Addresses.</p>
                  </header>
                  <office-addresses
                    :addresses.sync="addresses"
                    :registeredAddress.sync="registeredAddress"
                    :recordsAddress.sync="recordsAddress"
                    :asOfDate="asOfDate"
                    :componentEnabled="allowChange('coa')"
                    @modified="officeModifiedEventHandler($event)"
                    @valid="addressFormValid = $event"
                  />
                </section>

                <!-- Directors -->
                <section v-show="agmDate || noAgm">
                  <header>
                    <h2 id="AR-step-3-header">3. Directors</h2>
                    <p v-if="allowChange('cod')">Tell us who was elected or appointed and who ceased to be
                      a director at your {{ARFilingYear}} AGM.</p>
                    <p v-else>This is your list of directors active as of {{asOfDate}}, including
                      directors that were ceased at a later date.</p>
                  </header>
                  <directors ref="directorsList"
                    @directorsChange="directorsChange"
                    @directorsFreeChange="directorsFreeChange"
                    @allDirectors="allDirectors=$event"
                    @directorFormValid="directorFormValid=$event"
                    @directorEditAction="directorEditInProgress=$event"
                    :asOfDate="asOfDate"
                    :componentEnabled="allowChange('cod')"
                  />
                </section>
              </template>
            </article>

            <!-- BCOMP only: -->
            <article
              class="annual-report-article"
              v-if="entityFilter(EntityTypes.BCOMP)"
            >
              <!-- Page Title -->
              <header>
                <h1 id="AR-header-BC">File {{ARFilingYear}} Annual Report
                  <span style="font-style: italic" v-if="reportState"> &mdash; {{reportState}}</span>
                </h1>
                <p>Please review all the information before you file and pay.</p>
              </header>

              <!-- Business Details -->
              <section>
                <header>
                  <h2 id="AR-header-1-BC">1. Business Details</h2>
                </header>
                <ar-date />
                <br>
                <summary-office-addresses
                  :registeredAddress="registeredAddress"
                  :recordsAddress="recordsAddress"
                />
              </section>

              <!-- Directors -->
              <section>
                <header>
                  <h2 id="AR-header-2-BC">2. Directors</h2>
                </header>
                <summary-directors
                  :directors="directors"
                />
              </section>
            </article>

            <!-- Both COOP and BCOMP: -->

            <!-- Certify -->
            <section v-show="entityFilter(EntityTypes.BCOMP) || agmDate || noAgm">
              <header>
                <h2 id="AR-step-4-header" v-if="entityFilter(EntityTypes.BCOMP)">3. Certify Correct</h2>
                <h2 id="AR-step-4-header" v-else>4. Certify Correct</h2>
                <p>Enter the legal name of the current director, officer, or lawyer submitting this Annual Report.</p>
              </header>
              <certify
                :isCertified.sync="isCertified"
                :certifiedBy.sync="certifiedBy"
                :entityDisplay="displayName()"
                :message="certifyMessage"
                @valid="certifyFormValid=$event"
              />
            </section>

            <!-- Staff Payment -->
            <section v-if="isRoleStaff && isPayRequired" v-show="entityFilter(EntityTypes.BCOMP) || agmDate || noAgm">
              <header>
                <h2 id="AR-step-5-header">5. Staff Payment</h2>
              </header>
              <staff-payment
                :value.sync="routingSlipNumber"
                @valid="staffPaymentFormValid=$event"
              />
            </section>
          </section>
        </v-col>

        <v-col cols="12" lg="3" style="position: relative">
          <aside>
            <affix relative-element-selector=".annual-report-article" :offset="{ top: 120, bottom: 40 }">
              <sbc-fee-summary
                v-bind:filingData="[...filingData]"
                v-bind:payURL="payAPIURL"
                @total-fee="totalFee=$event"
              />
            </affix>
          </aside>
        </v-col>
      </v-row>
    </v-container>

    <!-- Buttons ( COOP only ) -->
    <v-container
      id="coop-buttons-container"
      class="list-item"
      v-if="entityFilter(EntityTypes.COOP)"
    >
      <div class="buttons-left">
        <v-btn id="ar-save-btn" large
          v-if="isAnnualReportEditable"
          :disabled="!isSaveButtonEnabled || busySaving"
          :loading="saving"
          @click="onClickSave()"
        >
          <span>Save</span>
        </v-btn>
        <v-btn id="ar-save-resume-btn" large
          v-if="isAnnualReportEditable"
          :disabled="!isSaveButtonEnabled || busySaving"
          :loading="savingResuming"
          @click="onClickSaveResume()"
        >
          <span>Save &amp; Resume Later</span>
        </v-btn>
      </div>

      <div class="buttons-right">
        <v-tooltip top color="#3b6cff">
          <template v-slot:activator="{ on }">
            <div v-on="on" class="d-inline">
              <v-btn
                v-if="isAnnualReportEditable"
                id="ar-file-pay-btn"
                color="primary"
                large
                :disabled="!validated || busySaving"
                :loading="filingPaying"
                @click="onClickFilePay()"
              >
                <span>{{isPayRequired ? "File &amp; Pay" : "File"}}</span>
              </v-btn>
            </div>
          </template>
          <span>Ensure all of your information is entered correctly before you File.<br>
            There is no opportunity to change information beyond this point.</span>
        </v-tooltip>

        <v-btn id="ar-cancel-btn" large to="/dashboard" :disabled="busySaving || filingPaying">Cancel</v-btn>
      </div>
    </v-container>

    <!-- Buttons ( BCOMP only ) -->
    <v-container
      id="bcorp-buttons-container"
      class="list-item"
      v-if="entityFilter(EntityTypes.BCOMP)"
    >
      <div class="buttons-left">
        <v-btn id="ar-back-btn" large to="/dashboard" :loading="filingPaying">Back</v-btn>
      </div>

      <div class="buttons-right">
        <v-tooltip top color="#3b6cff">
          <template v-slot:activator="{ on }">
            <div v-on="on" class="d-inline">
              <v-btn
                id="ar-file-pay-bc-btn"
                color="primary"
                large
                :disabled="!validated"
                :loading="filingPaying"
                @click="onClickFilePay()"
              >
                <span>File &amp; Pay</span>
              </v-btn>
            </div>
          </template>
          <span>Ensure all of your information is entered correctly before you File.<br>
            There is no opportunity to change information beyond this point.</span>
        </v-tooltip>
      </div>
    </v-container>
  </div>
</template>

<script lang="ts">
// Libraries
import axios from '@/axios-auth'
import { mapState, mapGetters } from 'vuex'
import { BAD_REQUEST, PAYMENT_REQUIRED } from 'http-status-codes'

// Components
import AgmDate from '@/components/AnnualReport/AGMDate.vue'
import ArDate from '@/components/AnnualReport/BCorp/ARDate.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'
import { OfficeAddresses, SummaryDirectors, SummaryOfficeAddresses } from '@/components/common'

// Dialogs
import { ConfirmDialog, PaymentErrorDialog, ResumeErrorDialog, SaveErrorDialog } from '@/components/dialogs'

// Mixins
import { DateMixin, EntityFilterMixin, ResourceLookupMixin } from '@/mixins'

// Constants
import { APPOINTED, CEASED, NAMECHANGED, ADDRESSCHANGED } from '@/constants'

// Interfaces
import { FilingData } from '@/interfaces'

// Enums
import { EntityTypes, FilingCodes } from '@/enums'

export default {
  name: 'AnnualReport',

  mixins: [DateMixin, EntityFilterMixin, ResourceLookupMixin],

  components: {
    ArDate,
    AgmDate,
    OfficeAddresses,
    Directors,
    Certify,
    StaffPayment,
    SbcFeeSummary,
    SummaryOfficeAddresses,
    SummaryDirectors,
    ConfirmDialog,
    PaymentErrorDialog,
    ResumeErrorDialog,
    SaveErrorDialog
  },

  data () {
    return {
      // properties for AgmDate component
      newAgmDate: null, // for resuming draft
      newNoAgm: null, // for resuming draft
      agmDate: null,
      noAgm: null,
      agmDateValid: false,

      // properties for OfficeAddresses component
      addresses: null,
      addressesFormValid: true,

      // properties for Directors component
      allDirectors: [],
      directorFormValid: true,
      directorEditInProgress: false,

      // properties for Certify component
      certifiedBy: '',
      isCertified: false,
      certifyFormValid: null,

      // properties for StaffPayment component
      routingSlipNumber: null,
      staffPaymentFormValid: false,
      totalFee: 0,

      // flags for displaying dialogs
      resumeErrorDialog: false,
      saveErrorDialog: false,
      paymentErrorDialog: false,

      // other local properties
      filingId: null,
      loadingMessage: 'Loading...', // initial generic message
      filingData: [] as Array<FilingData>,
      saving: false,
      savingResuming: false,
      filingPaying: false,
      haveChanges: false,
      saveErrors: [],
      saveWarnings: [],

      // enums
      EntityTypes,
      FilingCodes
    }
  },

  computed: {
    ...mapState(['currentDate', 'ARFilingYear', 'nextARDate', 'lastAgmDate', 'entityType', 'entityName',
      'entityIncNo', 'entityFoundingDate', 'registeredAddress', 'recordsAddress', 'lastPreLoadFilingDate',
      'directors']),

    ...mapGetters(['isRoleStaff', 'isAnnualReportEditable', 'reportState', 'lastCOAFilingDate', 'lastCODFilingDate']),

    /**
     * The As Of date, used to query data, as Effective Date, and as Annual Report Date.
     */
    asOfDate () {
      // if AGM Date is not empty then use it
      if (this.agmDate) return this.agmDate
      // if filing is in past year then use last day in that year
      if (this.ARFilingYear < this.currentYear) return `${this.ARFilingYear}-12-31`
      // otherwise use current date
      // (should never happen because either we should have an AGM Date or filing should be in past year)
      return this.currentDate
    },

    /**
     * The current year.
     */
    currentYear (): number {
      return this.currentDate ? +this.currentDate.substring(0, 4) : 0
    },

    certifyMessage () {
      if (this.entityFilter(EntityTypes.BCOMP)) {
        return this.certifyText(FilingCodes.ANNUAL_REPORT_BC)
      }
      return this.certifyText(FilingCodes.ANNUAL_REPORT_OT)
    },

    payAPIURL () {
      return sessionStorage.getItem('PAY_API_URL')
    },

    validated () {
      const staffPaymentValid = (!this.isRoleStaff || !this.isPayRequired || this.staffPaymentFormValid)

      if (this.entityFilter(EntityTypes.COOP)) {
        return (staffPaymentValid && this.agmDateValid && this.addressesFormValid && this.directorFormValid &&
              this.certifyFormValid && !this.directorEditInProgress)
      }
      return (staffPaymentValid && this.certifyFormValid)
    },

    busySaving () {
      return (this.saving || this.savingResuming || this.filingPaying)
    },

    isSaveButtonEnabled () {
      return (this.agmDateValid && this.addressesFormValid && this.directorFormValid && !this.directorEditInProgress)
    },

    isPayRequired () {
      // FUTURE: modify rule here as needed
      return (this.totalFee > 0)
    }
  },

  created () {
    // before unloading this page, if there are changes then prompt user
    window.onbeforeunload = (event) => {
      if (this.haveChanges) {
        event.preventDefault()
        // NB: custom text is not supported in all browsers
        event.returnValue = 'You have unsaved changes. Are you sure you want to leave?'
      }
    }
    // NB: filing id of 0 means "new AR"
    // otherwise it's a draft AR filing id
    this.filingId = this.$route.params.id

    // if tombstone data isn't set, route to home
    if (!this.entityIncNo || !this.ARFilingYear || (this.filingId === undefined)) {
      this.$router.push('/')
    } else if (this.filingId > 0) {
      // resume draft filing
      this.loadingMessage = `Resuming Your ${this.ARFilingYear} Annual Report`
      this.fetchData()
    } else {
      // else just load new page
      this.loadingMessage = `Preparing Your ${this.ARFilingYear} Annual Report`
    }
  },

  beforeRouteLeave (to, from, next) {
    if (!this.haveChanges) {
      // no changes -- resolve promise right away
      next()
      return
    }

    // open confirmation dialog and wait for response
    this.$refs.confirm.open(
      'Unsaved Changes',
      'You have unsaved changes in your Annual Report. Do you want to exit your filing?',
      {
        width: '40rem',
        persistent: true,
        yes: 'Return to my filing',
        no: null,
        cancel: 'Exit without saving'
      }
    ).then(async (confirm) => {
      // if we get here, Yes was clicked
      if (confirm) {
        next(false)
      }
    }).catch(() => {
      // if we get here, Cancel was clicked
      this.haveChanges = false
      next()
    })
  },

  methods: {
    fetchData () {
      const url = this.entityIncNo + '/filings/' + this.filingId
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

            this.certifiedBy = filing.header.certifiedBy
            this.routingSlipNumber = filing.header.routingSlipNumber

            // load Annual Report fields
            const annualReport = filing.annualReport
            if (annualReport) {
              // set the Draft Date in the Directors List component
              // FUTURE: use props instead of $refs (which cause an error in the unit tests)
              if (this.$refs.directorsList && this.$refs.directorsList.setDraftDate) {
                this.$refs.directorsList.setDraftDate(annualReport.annualGeneralMeetingDate)
              }
              if (this.entityFilter(EntityTypes.COOP)) {
                // set the new AGM date in the AGM Date component (may be null or empty)
                this.newAgmDate = annualReport.annualGeneralMeetingDate || ''
                // set the new No AGM flag in the AGM Date component (may be undefined)
                this.newNoAgm = annualReport.didNotHoldAgm || false
              }
            } else {
              throw new Error('missing annual report')
            }

            // load Change of Directors fields
            const changeOfDirectors = filing.changeOfDirectors
            if (changeOfDirectors) {
              if (changeOfDirectors.directors && changeOfDirectors.directors.length > 0) {
                if (this.$refs.directorsList && this.$refs.directorsList.setAllDirectors) {
                  this.$refs.directorsList.setAllDirectors(changeOfDirectors.directors)
                }

                // add filing code for paid changes
                if (changeOfDirectors.directors.filter(
                  director => this.hasAction(director, CEASED) || this.hasAction(director, APPOINTED)
                ).length > 0) {
                  this.toggleFiling('add', FilingCodes.DIRECTOR_CHANGE_OT)
                }

                // add filing code for free changes
                if (changeOfDirectors.directors.filter(
                  director => this.hasAction(director, NAMECHANGED) || this.hasAction(director, ADDRESSCHANGED)
                ).length > 0) {
                  this.toggleFiling('add', FilingCodes.FREE_DIRECTOR_CHANGE_OT)
                }
              } else {
                throw new Error('invalid change of directors')
              }
            } else {
              // To handle the condition of save as draft without change of director
              if (this.$refs.directorsList && this.$refs.directorsList.getDirectors) {
                this.$refs.directorsList.getDirectors()
              }
            }

            // load Change of Address fields
            if (filing.changeOfAddress) {
              const offices = filing.changeOfAddress.offices
              if (offices && offices.registeredOffice) {
                this.addresses = {
                  registeredOffice: {
                    deliveryAddress: offices.registeredOffice.deliveryAddress,
                    mailingAddress: offices.registeredOffice.mailingAddress
                  }
                }
                this.toggleFiling('add', FilingCodes.ADDRESS_CHANGE_OT)
              } else {
                throw new Error('invalid change of address')
              }
            }
          } catch (err) {
            // eslint-disable-next-line no-console
            console.log(`fetchData() error - ${err.message}, filing =`, filing)
            this.resumeErrorDialog = true
          }
        } else {
          // eslint-disable-next-line no-console
          console.log('fetchData() error - invalid response =', response)
          this.resumeErrorDialog = true
        }
      }).catch(error => {
        // eslint-disable-next-line no-console
        console.error('fetchData() error =', error)
        this.resumeErrorDialog = true
      })
    },

    /**
     * Callback method for the "modified" event from OfficeAddress.
     *
     * @param modified a boolean indicating whether or not the office address(es) have been modified from their
     * original values.
     */
    officeModifiedEventHandler (modified: boolean): void {
      this.haveChanges = true
      // when addresses change, update filing data
      this.toggleFiling(modified ? 'add' : 'remove', FilingCodes.ADDRESS_CHANGE_OT)
    },

    directorsChange (modified: boolean) {
      this.haveChanges = true
      // when directors change, update filing data
      this.toggleFiling(modified ? 'add' : 'remove', FilingCodes.DIRECTOR_CHANGE_OT)
    },

    directorsFreeChange (modified: boolean) {
      this.haveChanges = true
      // when directors change (free filing), update filing data
      this.toggleFiling(modified ? 'add' : 'remove', FilingCodes.FREE_DIRECTOR_CHANGE_OT)
    },

    onAgmDateChange (val: string) {
      this.haveChanges = true
      this.agmDate = val
    },

    onNoAgmChange (val: boolean) {
      this.haveChanges = true
      this.noAgm = val
    },

    onAgmDateValidChange (val: boolean) {
      this.agmDateValid = val
      // when validity changes, update filing data
      this.toggleFiling(val ? 'add' : 'remove', FilingCodes.ANNUAL_REPORT_OT)
    },

    async onClickSave () {
      // prevent double saving
      if (this.busySaving) return

      this.saving = true
      const filing = await this.saveFiling(true)
      if (filing) {
        // save Filing ID for future PUTs
        this.filingId = +filing.header.filingId
      }
      this.saving = false
    },

    async onClickSaveResume () {
      // prevent double saving
      if (this.busySaving) return

      this.savingResuming = true
      const filing = await this.saveFiling(true)
      // on success, route to Home URL
      if (filing) {
        this.$router.push('/')
      }
      this.savingResuming = false
    },

    async onClickFilePay () {
      // prevent double saving
      if (this.busySaving) return

      this.filingPaying = true
      const filing = await this.saveFiling(false) // not a draft

      // on success, redirect to Pay URL
      if (filing && filing.header) {
        const filingId = +filing.header.filingId

        // whether this is a staff or no-fee filing
        const prePaidFiling = (this.isRoleStaff || !this.isPayRequired)

        // if filing needs to be paid, redirect to Pay URL
        if (!prePaidFiling) {
          const paymentToken = filing.header.paymentToken
          const baseUrl = sessionStorage.getItem('BASE_URL')
          const returnURL = encodeURIComponent(baseUrl + 'dashboard?filing_id=' + filingId)
          const authUrl = sessionStorage.getItem('AUTH_URL')
          const payURL = authUrl + 'makepayment/' + paymentToken + '/' + returnURL

          // assume Pay URL is always reachable
          // otherwise, user will have to retry payment later
          window.location.assign(payURL)
        } else {
          // route directly to dashboard
          this.$router.push('/dashboard?filing_id=' + filingId)
        }
      }
      this.filingPaying = false
    },

    async saveFiling (isDraft) {
      this.resetErrors()

      const hasPendingFilings = await this.hasTasks(this.entityIncNo)
      if (hasPendingFilings) {
        this.saveErrors = [
          { error: 'Another draft filing already exists. Please complete it before creating a new filing.' }
        ]
        this.saveErrorDialog = true
        return null
      }

      let annualReport = null
      let changeOfDirectors = null
      let changeOfAddress = null

      const header = {
        header: {
          name: 'annualReport',
          certifiedBy: this.certifiedBy || '',
          email: 'no_one@never.get',
          date: this.currentDate,
          effectiveDate: this.asOfDate + 'T00:00:00+00:00'
        }
      }
      // only save this if it's not null
      if (this.routingSlipNumber) {
        header.header['routingSlipNumber'] = this.routingSlipNumber
      }

      const business = {
        business: {
          foundingDate: this.entityFoundingDate,
          identifier: this.entityIncNo,
          legalName: this.entityName
        }
      }

      if (this.entityFilter(EntityTypes.COOP)) {
        annualReport = {
          annualReport: {
            annualGeneralMeetingDate: this.agmDate || null, // API doesn't validate empty string
            didNotHoldAgm: this.noAgm || false,
            annualReportDate: this.asOfDate,
            offices: {
              registeredOffice: {
                deliveryAddress: this.addresses.registeredOffice['deliveryAddress'],
                mailingAddress: this.addresses.registeredOffice['mailingAddress']
              }
            },
            directors: this.allDirectors.filter(el => el.cessationDate === null)
          }
        }
      } else {
        annualReport = {
          annualReport: {
            annualReportDate: this.asOfDate,
            nextARDate: this.dateToUsableString(new Date(this.nextARDate)),
            offices: {
              registeredOffice: {
                deliveryAddress: this.registeredAddress['deliveryAddress'],
                mailingAddress: this.registeredAddress['mailingAddress']
              },
              recordsOffice: {
                deliveryAddress: this.recordsAddress['deliveryAddress'],
                mailingAddress: this.recordsAddress['mailingAddress']
              }
            },
            directors: this.directors
          }
        }
      }

      if (this.isDataChanged(FilingCodes.DIRECTOR_CHANGE_OT) ||
        this.isDataChanged(FilingCodes.FREE_DIRECTOR_CHANGE_OT)) {
        changeOfDirectors = {
          changeOfDirectors: {
            directors: this.allDirectors
          }
        }
      }

      if (this.isDataChanged(FilingCodes.ADDRESS_CHANGE_OT) && this.addresses) {
        changeOfAddress = {
          changeOfAddress: {
            legalType: this.entityType,
            offices: {
              registeredOffice: {
                deliveryAddress: this.addresses.registeredOffice['deliveryAddress'],
                mailingAddress: this.addresses.registeredOffice['mailingAddress']
              }
            }
          }
        }
      }

      const data = {
        filing: Object.assign(
          {},
          header,
          business,
          annualReport,
          changeOfAddress,
          changeOfDirectors
        )
      }

      if (this.filingId > 0) {
        // we have a filing id, so we are updating an existing filing
        let url = this.entityIncNo + '/filings/' + this.filingId
        if (isDraft) {
          url += '?draft=true'
        }
        let filing = null
        await axios.put(url, data).then(res => {
          if (!res || !res.data || !res.data.filing) {
            throw new Error('invalid API response')
          }
          filing = res.data.filing
          this.haveChanges = false
        }).catch(error => {
          if (error && error.response && error.response.status === PAYMENT_REQUIRED) {
            this.paymentErrorDialog = true
          } else if (error && error.response && error.response.status === BAD_REQUEST) {
            if (error.response.data.errors) {
              this.saveErrors = error.response.data.errors
            }
            if (error.response.data.warnings) {
              this.saveWarnings = error.response.data.warnings
            }
            this.saveErrorDialog = true
          } else {
            this.saveErrorDialog = true
          }
        })
        return filing
      } else {
        // filing id is 0, so we are saving a new filing
        let url = this.entityIncNo + '/filings'
        if (isDraft) {
          url += '?draft=true'
        }
        let filing = null
        await axios.post(url, data).then(res => {
          if (!res || !res.data || !res.data.filing) {
            throw new Error('invalid API response')
          }
          filing = res.data.filing
          this.haveChanges = false
        }).catch(error => {
          if (error && error.response && error.response.status === PAYMENT_REQUIRED) {
            this.paymentErrorDialog = true
          } else if (error && error.response && error.response.status === BAD_REQUEST) {
            if (error.response.data.errors) {
              this.saveErrors = error.response.data.errors
            }
            if (error.response.data.warnings) {
              this.saveWarnings = error.response.data.warnings
            }
            this.saveErrorDialog = true
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
        this.filingData.push({ filingTypeCode: filing, entityType: this.entityType })
      }
    },

    isDataChanged (key) {
      return this.filingData.find(o => o.filingTypeCode === key)
    },

    navigateToDashboard () {
      this.haveChanges = false
      this.dialog = false
      this.$router.push('/dashboard')
    },

    resetErrors () {
      this.saveErrorDialog = false
      this.saveErrors = []
      this.saveWarnings = []
    },

    allowChange (type) {
      let earliestAllowedDate
      if (type === 'coa') {
        earliestAllowedDate = this.lastCOAFilingDate
      }
      if (type === 'cod') {
        earliestAllowedDate = this.lastCODFilingDate
      }
      return Boolean(
        this.agmDateValid && this.agmDate && this.compareDates(this.agmDate, earliestAllowedDate, '>=')
      )
    },

    hasAction (director, action) {
      if (director.actions.indexOf(action) >= 0) return true
      else return false
    },

    async hasTasks (businessId) {
      let hasPendingItems = false
      if (this.filingId === 0) {
        await axios.get(businessId + '/tasks')
          .then(response => {
            if (response && response.data && response.data.tasks) {
              response.data.tasks.forEach((task) => {
                if (task.task && task.task.filing &&
                  task.task.filing.header && task.task.filing.header.status !== 'NEW') {
                  hasPendingItems = true
                }
              })
            }
          })
          .catch(error => {
            // eslint-disable-next-line no-console
            console.error('hasTasks() error =', error)
            this.saveErrorDialog = true
          })
      }
      return hasPendingItems
    }
  },

  mounted () {
    // for BComp, add AR filing code now
    // for Coop, code is added when AGM Date becomes valid
    this.entityFilter(EntityTypes.BCOMP) && this.toggleFiling('add', FilingCodes.ANNUAL_REPORT_BC)
  },

  watch: {
    isCertified (val: boolean) {
      this.haveChanges = true
    },

    certifiedBy (val: string) {
      this.haveChanges = true
    },

    routingSlipNumber (val) {
      this.haveChanges = true
    }
  }
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/theme.scss';

article {
  .v-card {
    line-height: 1.2rem;
    font-size: 0.875rem;
  }
}

header p,
section p {
  color: $gray6;
}

section + section {
  margin-top: 3rem;
}

h1 {
  margin-bottom: 1.25rem;
  line-height: 2rem;
  letter-spacing: -0.01rem;
}

h2 {
  margin-bottom: 0.25rem;
  margin-top: 3rem;
  font-size: 1.125rem;
}

.as-of-date {
  margin-left: 0.25rem;
  font-weight: 300;
}

// Save & Filing Buttons
#coop-buttons-container,
#bcorp-buttons-container {
  padding-top: 2rem;
  border-top: 1px solid $gray5;

  .buttons-left {
    width: 50%;
  }

  .buttons-right {
    margin-left: auto;
  }

  .v-btn + .v-btn {
    margin-left: 0.5rem;
  }

  #ar-cancel-btn {
    margin-left: 0.5rem;
  }
}
</style>
