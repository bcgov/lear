<template>
  <div>
    <!-- Dialogs -->
    <ConfirmDialog ref="confirm" />

    <ResumeErrorDialog
      :dialog="resumeErrorDialog"
      @exit="navigateToDashboard"
    />

    <SaveErrorDialog
      filing="Annual Report"
      :dialog="saveErrorDialog"
      :disableRetry="busySaving"
      :errors="saveErrors"
      :warnings="saveWarnings"
      @exit="navigateToDashboard"
      @retry="onClickFilePay"
      @okay="resetErrors"
    />

    <PaymentErrorDialog
      :dialog="paymentErrorDialog"
      @exit="navigateToDashboard"
    />

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
            <p>Please verify or change your Office Addresses and Directors.</p>
          </header>

          <div v-if="isAnnualReportEditable">
            <!-- Annual General Meeting Date ( COOP ) -->
            <section v-if="entityFilter(EntityTypes.Coop)">
              <header>
                <h2 id="AR-step-1-header">1. Annual General Meeting Date</h2>
                <p>Select your Annual General Meeting (AGM) date</p>
              </header>
              <AGMDate
                :initialAgmDate="initialAgmDate"
                :allowCOA="allowChange('coa')"
                :allowCOD="allowChange('cod')"
                @agmDate="agmDate=$event"
                @noAGM="noAGM=$event"
                @valid="agmDateValid=$event"
              />
            </section>

            <!-- Annual Report Date ( BCORP ) -->
            <section v-if="entityFilter(EntityTypes.BCorp)">
              <header>
                <h2 id="AR-step-1-header-BC">1. Dates</h2>
                <p>Your Annual Report Date is the anniversary of the date your corporation was started.<br>
                  The information displayed on this form reflects the state of your corporation on this date each year.
                </p>
              </header>
              <ARDate />
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
                :changeButtonDisabled="!allowChange('coa')"
                :legalEntityNumber="entityIncNo"
                :addresses.sync="addresses"
                @modified="officeModifiedEventHandler($event)"
                @valid="addressesFormValid=$event"
              />
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
                @directorsFreeChange="directorsFreeChange"
                @allDirectors="allDirectors=$event"
                @directorFormValid="directorFormValid=$event"
                @directorEditAction="directorEditInProgress=$event"
                :asOfDate="agmDate"
                :componentEnabled="allowChange('cod')"
              />
            </section>

            <!-- Certify -->
            <section>
              <header>
                <h2 id="AR-step-4-header">4. Certify Correct</h2>
                <p>Enter the name of the current director, officer, or lawyer submitting this Annual Report.</p>
              </header>
              <Certify
                :isCertified.sync="isCertified"
                :certifiedBy.sync="certifiedBy"
                :currentDate="currentDate"
                @valid="certifyFormValid=$event"
              />
            </section>

            <!-- Staff Payment -->
            <section v-if="isRoleStaff && isPayRequired">
              <header>
                <h2 id="AR-step-5-header">5. Staff Payment</h2>
              </header>
              <StaffPayment
                :value.sync="routingSlipNumber"
                @valid="staffPaymentFormValid=$event"
              />
            </section>

          </div>
        </article>

        <aside>
          <affix relative-element-selector="#annual-report-article" :offset="{ top: 120, bottom: 40 }">
            <sbc-fee-summary
              v-bind:filingData="[...filingData]"
              v-bind:payURL="payAPIURL"
              @total-fee="totalFee=$event"
            />
          </affix>
        </aside>
      </v-container>

      <v-container id="buttons-container" class="list-item">
        <div class="buttons-left">
          <v-btn id="ar-save-btn" large
            v-if="isAnnualReportEditable"
            :disabled="!isSaveButtonEnabled || busySaving"
            :loading="saving"
            @click="onClickSave"
          >
            Save
          </v-btn>
          <v-btn id="ar-save-resume-btn" large
            v-if="isAnnualReportEditable"
            :disabled="!isSaveButtonEnabled || busySaving"
            :loading="savingResuming"
            @click="onClickSaveResume"
          >
            Save &amp; Resume Later
          </v-btn>
        </div>

        <div class="buttons-right">
          <v-tooltip top color="#3b6cff">
            <template v-slot:activator="{ on }">
              <div v-on="on" class="inline-div">
                <v-btn
                  v-if="isAnnualReportEditable"
                  id="ar-file-pay-btn"
                  color="primary"
                  large
                  :disabled="!validated || busySaving"
                  :loading="filingPaying"
                  @click="onClickFilePay"
                >
                  {{ isPayRequired ? "File &amp; Pay" : "File" }}
                </v-btn>
              </div>
            </template>
            <span>Ensure all of your information is entered correctly before you File.<br>
              There is no opportunity to change information beyond this point.</span>
          </v-tooltip>
          <v-btn
            id="ar-cancel-btn"
            large
            to="/dashboard"
          >
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
import ARDate from '@/components/AnnualReport/BCorp/ARDate.vue'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapGetters } from 'vuex'
import { BAD_REQUEST, PAYMENT_REQUIRED } from 'http-status-codes'
import Certify from '@/components/AnnualReport/Certify.vue'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import PaymentErrorDialog from '@/components/AnnualReport/PaymentErrorDialog.vue'
import ResumeErrorDialog from '@/components/AnnualReport/ResumeErrorDialog.vue'
import SaveErrorDialog from '@/components/AnnualReport/SaveErrorDialog.vue'
import DateMixin from '@/mixins/date-mixin'
import EntityFilterMixin from '@/mixins/entityFilter-mixin'
import { EntityTypes } from '@/enums'

// action constants
const APPOINTED = 'appointed'
const CEASED = 'ceased'
const NAMECHANGED = 'nameChanged'
const ADDRESSCHANGED = 'addressChanged'

export default {
  name: 'AnnualReport',

  mixins: [DateMixin, EntityFilterMixin],

  components: {
    ARDate,
    AGMDate,
    RegisteredOfficeAddress,
    Directors,
    Certify,
    StaffPayment,
    Affix,
    SbcFeeSummary,
    ConfirmDialog,
    PaymentErrorDialog,
    ResumeErrorDialog,
    SaveErrorDialog
  },

  data () {
    return {
      // properties for AGMDate component
      initialAgmDate: null,
      agmDate: null,
      noAGM: false,
      agmDateValid: false,

      // properties for RegisteredOfficeAddress component
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

      // properties for Staff Payment component
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
      filingData: [],
      saving: false,
      savingResuming: false,
      filingPaying: false,
      haveChanges: false,
      saveErrors: [],
      saveWarnings: [],

      // EntityTypes Enum
      EntityTypes
    }
  },

  computed: {
    ...mapState(['currentDate', 'ARFilingYear', 'lastAgmDate', 'entityType', 'entityName',
      'entityIncNo', 'entityFoundingDate', 'lastPreLoadFilingDate']),

    ...mapGetters(['isRoleStaff', 'isAnnualReportEditable', 'reportState', 'lastCOAFilingDate', 'lastCODFilingDate']),

    annualReportDate () {
      // AR Filing Year, but as a date field with today's month and day
      let thedate = new Date()
      thedate.setFullYear(this.ARFilingYear)
      return this.dateToUsableString(thedate)
    },

    payAPIURL () {
      return sessionStorage.getItem('PAY_API_URL')
    },

    validated () {
      const staffPaymentValid = (!this.isRoleStaff || !this.isPayRequired || this.staffPaymentFormValid)

      return (staffPaymentValid && this.agmDateValid && this.addressesFormValid && this.directorFormValid &&
        this.certifyFormValid && !this.directorEditInProgress)
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
              // TODO: use props instead of $refs (which cause an error in the unit tests)
              if (this.$refs.directorsList && this.$refs.directorsList.setDraftDate) {
                this.$refs.directorsList.setDraftDate(annualReport.annualGeneralMeetingDate)
              }
              // set the Initial AGM Date in the AGM Date component
              // NOTE: AR Filing Year (which is needed by agmDate component) was already set by Todo List
              this.initialAgmDate = annualReport.annualGeneralMeetingDate
              this.toggleFiling('add', 'OTANN')
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
                  this.toggleFiling('add', 'OTCDR')
                }

                // add filing code for free changes
                if (changeOfDirectors.directors.filter(
                  director => this.hasAction(director, NAMECHANGED) || this.hasAction(director, ADDRESSCHANGED)
                ).length > 0) {
                  this.toggleFiling('add', 'OTFDR')
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
      this.haveChanges = true
      // when addresses change, update filing data
      this.toggleFiling(modified ? 'add' : 'remove', 'OTADD')
    },

    directorsChange (modified: boolean) {
      this.haveChanges = true
      // when directors change, update filing data
      this.toggleFiling(modified ? 'add' : 'remove', 'OTCDR')
    },

    directorsFreeChange (modified: boolean) {
      this.haveChanges = true
      // when directors change (free filing), update filing data
      this.toggleFiling(modified ? 'add' : 'remove', 'OTFDR')
    },

    async onClickSave () {
      // prevent double saving
      if (this.busySaving) return

      this.saving = true
      const filing = await this.saveFiling(true)
      if (filing) {
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

      let changeOfDirectors = null
      let changeOfAddress = null

      const header = {
        header: {
          name: 'annualReport',
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

      const annualReport = {
        annualReport: {
          annualGeneralMeetingDate: this.noAGM ? null : this.agmDate,
          annualReportDate: this.annualReportDate,
          deliveryAddress: this.addresses['deliveryAddress'],
          mailingAddress: this.addresses['mailingAddress'],
          directors: this.allDirectors.filter(el => el.cessationDate === null)
        }
      }

      if (this.isDataChanged('OTCDR') || this.isDataChanged('OTFDR')) {
        changeOfDirectors = {
          changeOfDirectors: {
            directors: this.allDirectors
          }
        }
      }

      if (this.isDataChanged('OTADD') && this.addresses) {
        changeOfAddress = {
          changeOfAddress: {
            deliveryAddress: this.addresses['deliveryAddress'],
            mailingAddress: this.addresses['mailingAddress']
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
        if (isDraft) { url += '?draft=true' }
        let filing = null
        await axios.put(url, data).then(res => {
          if (!res || !res.data || !res.data.filing) { throw new Error('invalid API response') }
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
        if (isDraft) { url += '?draft=true' }
        let filing = null
        await axios.post(url, data).then(res => {
          if (!res || !res.data || !res.data.filing) { throw new Error('invalid API response') }
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
      } else if (type === 'cod') {
        earliestAllowedDate = this.lastCODFilingDate
      }
      if (!earliestAllowedDate) {
        earliestAllowedDate = this.lastPreLoadFilingDate
      }
      return this.agmDateValid && this.compareDates(this.agmDate, earliestAllowedDate, '>=')
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
            console.error('fetchData() error =', error)
            this.saveErrorDialog = true
          })
        return hasPendingItems
      }
    }
  },

  watch: {
    agmDate (val: string) {
      this.haveChanges = true
      // when AGM Date changes, update filing data
      this.toggleFiling(val ? 'add' : 'remove', 'OTANN')
    },

    noAGM (val: boolean) {
      this.haveChanges = true
      // when No AGM changes, update filing data
      this.toggleFiling(val ? 'add' : 'remove', 'OTANN')
    },

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

section p {
  color: $gray6;
}

section + section {
  margin-top: 3rem;
}

h2 {
  margin-bottom: 0.25rem;
  margin-top: 3rem;
  font-size: 1.125rem;
}

#AR-header {
  margin-bottom: 1.25rem;
  line-height: 2rem;
  letter-spacing: -0.01rem;
}

.title-container {
  margin-bottom: 0.5rem;
}

.agm-date {
  margin-left: 0.25rem;
  font-weight: 300;
}

// Save & Filing Buttons
#buttons-container {
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
