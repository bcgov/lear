<template>
  <div id="correction">
    <confirm-dialog
      ref="confirm"
      attach="#correction"
    />

    <load-correction-dialog
      :dialog="loadCorrectionDialog"
      @exit="navigateToDashboard"
      attach="#correction"
    />

    <resume-error-dialog
      :dialog="resumeErrorDialog"
      @exit="navigateToDashboard"
      attach="#correction"
    />

    <save-error-dialog
      filing="Correction"
      :dialog="saveErrorDialog"
      :disableRetry="busySaving"
      :errors="saveErrors"
      :warnings="saveWarnings"
      @exit="navigateToDashboard"
      @retry="onClickFilePay"
      @okay="resetErrors"
      attach="#correction"
    />

    <payment-error-dialog
      :dialog="paymentErrorDialog"
      @exit="navigateToDashboard"
      attach="#correction"
    />

    <!-- Initial Page Load Transition -->
    <transition name="fade">
      <div class="loading-container" v-show="showLoadingContainer">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate />
          <div class="loading-msg">{{loadingMessage}}</div>
        </div>
      </div>
    </transition>

    <v-container id="correction-container" class="view-container" v-show="dataLoaded">
      <v-row>
        <v-col cols="12" lg="9">
          <section>
            <article class="correction-article">
              <!-- Page Title -->
              <header>
                <h1 id="correction-header">Correction &mdash; {{title}}</h1>
                <p class="text-black">Original Filing Date: {{originalFilingDate}}</p>
              </header>
            </article>

            <!-- Detail Comment -->
            <section>
              <header>
                <h2 id="correction-step-1-header">1. Detail Comment</h2>
                <p>Enter a detail comment that will appear on the ledger for this entity.</p>
              </header>
              <detail-comment
                :comment.sync="detailComment"
                @valid="detailCommentValid=$event"
              />
            </section>

            <!-- Certify -->
            <section>
              <header>
                <h2 id="correction-step-2-header">2. Certify Correct</h2>
                <p>Enter the legal name of the current director, officer, or lawyer submitting this correction.</p>
              </header>
              <certify
                :isCertified.sync="isCertified"
                :certifiedBy.sync="certifiedBy"
                :entityDisplay="displayName()"
                :message="certifyText(FilingCodes.ANNUAL_REPORT_OT)"
                @valid="certifyFormValid=$event"
              />
            </section>

            <!-- Staff Payment -->
            <section v-if="isRoleStaff && isPayRequired">
              <header>
                <h2 id="correction-step-3-header">3. Staff Payment</h2>
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
            <affix relative-element-selector=".correction-article" :offset="{ top: 120, bottom: 40 }">
              <sbc-fee-summary
                :filingData="[...filingData]"
                :payURL="payAPIURL"
                :priority="true"
                :waiveFees="true"
                @total-fee="totalFee=$event"
              />
            </affix>
          </aside>
        </v-col>
      </v-row>
    </v-container>

    <!-- Buttons -->
    <v-container
      id="correction-buttons-container"
      class="list-item"
    >
      <div class="buttons-left">
        <!-- NB: no saving in Corrections 1.0 -->
        <!-- <v-btn id="ar-save-btn" large
          :disabled="!isSaveButtonEnabled || busySaving"
          :loading="saving"
          @click="onClickSave()"
        >
          <span>Save</span>
        </v-btn> -->
        <!-- <v-btn id="ar-save-resume-btn" large
          :disabled="!isSaveButtonEnabled || busySaving"
          :loading="savingResuming"
          @click="onClickSaveResume()"
        >
          <span>Save &amp; Resume Later</span>
        </v-btn> -->
      </div>

      <div class="buttons-right">
        <v-tooltip top color="#3b6cff">
          <template v-slot:activator="{ on }">
            <div v-on="on" class="d-inline">
              <v-btn
                id="ar-file-pay-btn"
                color="primary"
                large
                :disabled="!validated || busySaving"
                :loading="filingPaying"
                @click="onClickFilePay()"
              >
                <span>{{ isPayRequired ? "File &amp; Pay" : "File" }}</span>
              </v-btn>
            </div>
          </template>
          <span>Ensure all of your information is entered correctly before you File.<br>
            There is no opportunity to change information beyond this point.</span>
        </v-tooltip>

        <v-btn id="ar-cancel-btn" large to="/dashboard" :disabled="busySaving || filingPaying">Cancel</v-btn>
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
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import { DetailComment } from '@/components/common'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'

// Dialogs
import { ConfirmDialog, PaymentErrorDialog, LoadCorrectionDialog, ResumeErrorDialog, SaveErrorDialog }
  from '@/components/dialogs'

// Mixins
import { DateMixin, EntityFilterMixin } from '@/mixins'
import { ResourceLookupMixin } from '../mixins'

// Interfaces
import { FilingData } from '@/interfaces'

// Enums
import { FilingCodes, FilingNames, FilingStatus, FilingTypes, EntityTypes } from '@/enums'

export default {
  name: 'Correction',

  mixins: [DateMixin, EntityFilterMixin, ResourceLookupMixin],

  components: {
    Certify,
    DetailComment,
    StaffPayment,
    SbcFeeSummary,
    ConfirmDialog,
    PaymentErrorDialog,
    LoadCorrectionDialog,
    ResumeErrorDialog,
    SaveErrorDialog
  },

  data () {
    return {
      // properties for DetailComment component
      detailComment: '',
      detailCommentValid: false,

      // properties for Certify component
      certifiedBy: '',
      isCertified: false,
      certifyFormValid: null,

      // properties for Staff Payment component
      routingSlipNumber: null,
      staffPaymentFormValid: false,
      totalFee: 0,

      // flags for displaying dialogs
      loadCorrectionDialog: false,
      resumeErrorDialog: false,
      saveErrorDialog: false,
      paymentErrorDialog: false,

      // other program state
      dataLoaded: false,
      loadingMessage: 'Loading...', // initial generic message
      filingId: null, // id of this correction filing
      origFiling: null, // copy of original filing
      filingData: [] as Array<FilingData>,
      saving: false,
      savingResuming: false,
      filingPaying: false,
      haveChanges: false,
      saveErrors: [],
      saveWarnings: [],

      // enums
      FilingCodes,
      FilingNames,
      FilingStatus,
      FilingTypes,
      EntityTypes
    }
  },

  computed: {
    ...mapState(['currentDate', 'entityType', 'entityName', 'entityIncNo', 'entityFoundingDate']),

    ...mapGetters(['isRoleStaff']),

    showLoadingContainer (): boolean {
      return !this.dataLoaded && !this.loadCorrectionDialog
    },

    title (): string | null {
      if (this.origFiling && this.origFiling.header && this.origFiling.header.name) {
        switch (this.origFiling.header.name) {
          case FilingTypes.ANNUAL_REPORT: return `${FilingNames.ANNUAL_REPORT} (${this.agmYear})`
          case FilingTypes.CHANGE_OF_ADDRESS: return FilingNames.ADDRESS_CHANGE
          case FilingTypes.CHANGE_OF_DIRECTORS: return FilingNames.DIRECTOR_CHANGE
          case FilingTypes.CHANGE_OF_NAME: return FilingNames.LEGAL_NAME_CHANGE
          case FilingTypes.SPECIAL_RESOLUTION: return FilingNames.SPECIAL_RESOLUTION
          case FilingTypes.VOLUNTARY_DISSOLUTION: return FilingNames.VOLUNTARY_DISSOLUTION
        }
        // fallback for unknown filings
        return this.origFiling.header.name.split(/(?=[A-Z])/).join(' ').replace(/^\w/, c => c.toUpperCase())
      }
      return null
    },

    agmYear (): number | null {
      if (this.origFiling && this.origFiling.annualReport && this.origFiling.annualReport.annualReportDate) {
        const date = this.origFiling.annualReport.annualReportDate
        return +date.slice(0, 4)
      }
      return null
    },

    originalFilingDate (): string | null {
      if (this.origFiling && this.origFiling.header && this.origFiling.header.date) {
        const localDateTime = this.convertUTCTimeToLocalTime(this.origFiling.header.date)
        return localDateTime.split(' ')[0]
      }
      return null
    },

    payAPIURL (): string {
      return sessionStorage.getItem('PAY_API_URL')
    },

    validated (): boolean {
      // TODO: handle Waive Fees
      const staffPaymentValid = (!this.isRoleStaff || !this.isPayRequired || this.staffPaymentFormValid)
      return (staffPaymentValid && this.detailCommentValid && this.certifyFormValid)
    },

    busySaving (): boolean {
      return (this.saving || this.savingResuming || this.filingPaying)
    },

    isSaveButtonEnabled (): boolean {
      return true // FUTURE: add necessary logic here
    },

    isPayRequired (): boolean {
      // TODO: handle Waive Fees
      return (this.totalFee > 0)
    }
  },

  created (): void {
    // before unloading this page, if there are changes then prompt user
    window.onbeforeunload = (event) => {
      if (this.haveChanges) {
        event.preventDefault()
        // NB: custom text is not supported in all browsers
        event.returnValue = 'You have unsaved changes. Are you sure you want to leave?'
      }
    }
    // NB: this is the id of the filing to correct
    const origFilingId = this.$route.params.id

    // if required data isn't set, route to home
    if (!this.entityIncNo || (origFilingId === undefined) || (origFilingId <= 0)) {
      this.$router.push('/')
    } else {
      this.loadingMessage = `Preparing Your Correction`
      this.fetchOrigFiling(origFilingId)
    }
  },

  mounted (): void {
    // always include the $20 fee
    this.toggleFiling('add', FilingCodes.RESTORATION_CONVERT_BC)
  },

  beforeRouteLeave (to, from, next): void {
    if (!this.haveChanges) {
      // no changes -- resolve promise right away
      next()
      return
    }

    // open confirmation dialog and wait for response
    this.$refs.confirm.open(
      'Unsaved Changes',
      'You have unsaved changes in your Correction. Do you want to exit your filing?',
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
    // this is used to fetch the filing to correct
    // FUTURE: need another method to load the draft correction?
    fetchOrigFiling (origFilingId: number): void {
      this.dataLoaded = false

      const url = this.entityIncNo + '/filings/' + origFilingId
      axios.get(url).then(res => {
        if (res && res.data) {
          this.origFiling = res.data.filing
          try {
            // verify data
            if (!this.origFiling) throw new Error('missing filing')
            if (!this.origFiling.header) throw new Error('missing header')
            if (!this.origFiling.business) throw new Error('missing business')
            if (this.origFiling.header.status !== FilingStatus.COMPLETED) throw new Error('invalid filing status')
            if (this.origFiling.business.identifier !== this.entityIncNo) throw new Error('invalid business identifier')
            if (this.origFiling.business.legalName !== this.entityName) throw new Error('invalid business legal name')

            // restore original Certified By name
            this.certifiedBy = this.origFiling.header.certifiedBy || ''

            // initialize comment
            this.detailComment = `[Filing corrected on ${this.currentDate}]\n`
          } catch (err) {
            // eslint-disable-next-line no-console
            console.log(`fetchOrigFiling() error - ${err.message}, origFiling =`, this.origFiling)
            this.loadCorrectionDialog = true
          } finally {
            this.dataLoaded = true
          }
        } else {
          // eslint-disable-next-line no-console
          console.log('fetchOrigFiling() error - invalid response =', res)
          this.loadCorrectionDialog = true
        }
      }).catch(error => {
        // eslint-disable-next-line no-console
        console.error('fetchOrigFiling() error =', error)
        this.loadCorrectionDialog = true
      })
    },

    // FUTURE
    // async onClickSave: Promise<void> () {
    //   // prevent double saving
    //   if (this.busySaving) return

    //   this.saving = true
    //   const filing = await this.saveFiling(true)
    //   if (filing) {
    //     // save Filing ID for future PUTs
    //     this.filingId = +filing.header.filingId
    //   }
    //   this.saving = false
    // },

    // FUTURE
    // async onClickSaveResume (): Promise<void> {
    //   // prevent double saving
    //   if (this.busySaving) return

    //   this.savingResuming = true
    //   const filing = await this.saveFiling(true)
    //   // on success, route to Home URL
    //   if (filing) {
    //     this.$router.push('/')
    //   }
    //   this.savingResuming = false
    // },

    async onClickFilePay (): Promise<void> {
      // prevent double saving
      if (this.busySaving) return

      this.filingPaying = true
      const filing = await this.saveFiling(false) // not a draft

      // on success, redirect to Pay URL
      if (filing && filing.header) {
        const filingId = +filing.header.filingId

        // whether this is a staff or no-fee filing
        // TODO: handle Waive Fees
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

    async saveFiling (isDraft): Promise<any> {
      this.resetErrors()

      const hasPendingFilings = await this.hasTasks(this.entityIncNo)
      if (hasPendingFilings) {
        this.saveErrors = [
          { error: 'Another draft filing already exists. Please complete it before creating a new filing.' }
        ]
        this.saveErrorDialog = true
        return null
      }

      const header = {
        header: {
          name: 'correction',
          certifiedBy: this.certifiedBy || '',
          email: 'no_one@never.get',
          date: this.currentDate
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

      const correction = {
        correction: {
          // FUTURE: add more properties here
          origFilingId: this.origFilingId,
          name: this.origFiling.header.name, // aka type
          comment: this.detailComment
        }
      }

      const data = {
        filing: Object.assign(
          {},
          header,
          business,
          correction
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

    toggleFiling (setting, filing): void {
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
        // TODO: remove hard-coded entity type when fee codes are available from Pay team
        // this.filingData.push({ filingTypeCode: filing, entityType: this.entityType })
        this.filingData.push({ filingTypeCode: filing, entityType: EntityTypes.BCOMP })
      }
    },

    isDataChanged (key): boolean {
      return this.filingData.find(o => o.filingTypeCode === key)
    },

    navigateToDashboard (): void {
      this.haveChanges = false
      this.dialog = false
      this.$router.push('/dashboard')
    },

    resetErrors (): void {
      this.saveErrorDialog = false
      this.saveErrors = []
      this.saveWarnings = []
    },

    async hasTasks (businessId): Promise<boolean> {
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
            console.error('fetchData() error =', error)
            this.saveErrorDialog = true
          })
      }
      return hasPendingItems
    }
  },

  watch: {
    detailCommentValid (val: boolean): void {
      console.log('detailCommentValid =', val) // FOR DEBUGGING ONLY
      this.haveChanges = true
    },

    certifyFormValid (val: boolean): void {
      console.log('certifyFormValid =', val)
      this.haveChanges = true
    },

    staffPaymentFormValid (val: boolean): void {
      console.log('staffPaymentFormValid =', val)
      this.haveChanges = true
    }
  }
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/theme.scss';

.text-black {
  color: rgba(0,0,0,.87);
}

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

// Save & Filing Buttons
#correction-buttons-container {
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
