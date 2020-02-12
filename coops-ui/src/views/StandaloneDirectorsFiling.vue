<template>
  <div id="standalone-directors">
    <confirm-dialog
      ref="confirm"
      attach="#standalone-directors"
    />

    <resume-error-dialog
      :dialog="resumeErrorDialog"
      @exit="navigateToDashboard"
      attach="#standalone-directors"
    />

    <save-error-dialog
      filing="Change of Directors"
      :dialog="saveErrorDialog"
      :disableRetry="busySaving"
      :errors="saveErrors"
      :warnings="saveWarnings"
      @exit="navigateToDashboard"
      @retry="onClickFilePay"
      @okay="resetErrors"
      attach="#standalone-directors"
    />

    <payment-error-dialog
      :dialog="paymentErrorDialog"
      @exit="navigateToDashboard"
      attach="#standalone-directors"
    />

    <!-- Initial Page Load Transition -->
    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
        <div class="loading-msg">{{loadingMessage}}</div>
      </div>
    </div>

    <!-- Change of Directors Filing -->
    <v-fade-transition hide-on-leave>
      <div v-show="!inFilingReview">
        <v-container id="standalone-directors-container" class="view-container">
          <v-row>
            <v-col cols="12" lg="9">
              <article id="standalone-directors-article">
                <header>
                  <h1 id="filing-header">Director Change</h1>
                  <p>Select the date of your director changes. If you have director changes that occured on
                      different dates, you will need to perform multiple Director Change filings &mdash;
                      one for each unique date.</p>

                  <v-alert type="info" outlined
                    v-if="!entityFilter(EntityTypes.BCOMP)"
                    icon="mdi-information"
                    class="white-background"
                  >
                    <span>Director changes can be made as far back as {{earliestDateToSet}}.</span>
                  </v-alert>
                </header>

                <section>
                  <cod-date
                    :initialCODDate="initialCODDate"
                    @codDate="codDate=$event"
                    @valid="codDateValid=$event"
                  />
                </section>

                <!-- Director Information -->
                <section>
                  <directors ref="directorsList"
                    @directorsChange="directorsChange"
                    @directorsFreeChange="directorsFreeChange"
                    @earliestDateToSet="earliestDateToSet=$event"
                    @directorFormValid="directorFormValid=$event"
                    @allDirectors="allDirectors=$event"
                    @directorEditAction="directorEditInProgress=$event"
                    @complianceDialogMsg="complianceDialogMsg=$event"
                    :asOfDate="codDate"
                  />
                </section>

                <!-- Certify -->
                <section>
                  <header>
                    <h2 id="AR-step-4-header">Certify Correct</h2>
                    <p>Enter the legal name of the current director, officer, or lawyer submitting this
                      Director Change.</p>
                  </header>
                  <certify
                    :isCertified.sync="isCertified"
                    :certifiedBy.sync="certifiedBy"
                    :entityDisplay="displayName()"
                    :message="certifyText(FilingCodes.DIRECTOR_CHANGE_OT)"
                    @valid="certifyFormValid=$event"
                  />
                </section>

                <!-- Staff Payment -->
                <section v-if="isRoleStaff && isPayRequired">
                  <header>
                    <h2 id="AR-step-5-header">Staff Payment</h2>
                  </header>
                  <staff-payment
                    :value.sync="routingSlipNumber"
                    @valid="staffPaymentFormValid=$event"
                  />
                </section>
              </article>
            </v-col>

            <v-col cols="12" lg="3" style="position: relative">
              <aside>
                <affix
                  relative-element-selector="#standalone-directors-article"
                  :offset="{ top: 120, bottom: 40 }"
                >
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

        <!-- TODO: this container should have some container class not 'list-item' class -->
        <v-container id="standalone-directors-buttons-container" class="list-item">
          <div class="buttons-left">
            <v-btn id="cod-save-btn" large
              :disabled="!isSaveButtonEnabled || busySaving"
              :loading="saving"
              @click="onClickSave()"
            >
              <span>Save</span>
            </v-btn>
            <v-btn id="cod-save-resume-btn" large
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
                    id="cod-next-btn"
                    color="primary"
                    large
                    :disabled="!validated || busySaving"
                    :loading="filingPaying"
                    @click="showSummary()"
                  >
                    <span>Next</span>
                  </v-btn>
                </div>
              </template>
              <span>Proceed to Filing Summary</span>
            </v-tooltip>

            <v-btn id="cod-cancel-btn" large to="/dashboard" :disabled="busySaving || filingPaying">Cancel</v-btn>
          </div>
        </v-container>
      </div>
    </v-fade-transition>

    <!-- Change of Directors Filing Summary -->
    <v-fade-transition hide-on-leave>
      <div v-show="inFilingReview">
        <v-container id="standalone-directors-container-review" class="view-container">
          <v-row>
            <v-col cols="12" lg="9">
              <article id="standalone-directors-article-review">
                <header>
                  <h1 id="filing-header-review">Review: Director Change </h1>
                </header>
                <section v-if="complianceDialogMsg">
                  <v-alert type="info" outlined
                    icon="mdi-information"
                    class="white-background"
                  >
                    <p class="complianceDialogMsg">{{complianceDialogMsg.msg}}</p>
                  </v-alert>
                </section>
                <!-- Director Information -->
                <section>
                  <summary-directors
                    :directors="allDirectors"
                  />
                </section>

                <!-- Certify -->
                <section>
                  <header>
                    <h2>Certify Correct</h2>
                  </header>
                  <summary-certify
                    :isCertified.sync="isCertified"
                    :certifiedBy.sync="certifiedBy"
                    :entityDisplay="displayName()"
                    :message="certifyText(FilingCodes.DIRECTOR_CHANGE_OT)"
                    @valid="certifyFormValid=$event"
                  />
                </section>

                <!-- Staff Payment -->
                <section v-if="isRoleStaff && isPayRequired">
                  <header>
                    <h2>Staff Payment</h2>
                  </header>
                  <summary-staff-payment
                    :value="routingSlipNumber"
                  />
                </section>
              </article>
            </v-col>

            <v-col cols="12" lg="3" style="position: relative">
              <aside>
                <affix
                  relative-element-selector="#standalone-directors-article-review"
                  :offset="{ top: 120, bottom: 40 }"
                >
                  <sbc-fee-summary
                    v-bind:filingData="[...filingData]"
                    v-bind:payURL="payAPIURL"
                  />
                </affix>
              </aside>
            </v-col>
          </v-row>
        </v-container>

        <!-- TODO: this container should have some container class not 'list-item' class -->
        <v-container id="standalone-directors-buttons-container-review" class="list-item">
          <div class="buttons-left">
            <v-btn
              id="cod-back-btn"
              large
              @click="returnToFiling()"
            >
              <span>Back</span>
            </v-btn>
          </div>

          <div class="buttons-right">
            <v-tooltip top color="#3b6cff">
              <template v-slot:activator="{ on }">
                <div v-on="on" class="d-inline">
                  <v-btn
                    id="cod-file-pay-btn"
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
          </div>
        </v-container>
      </div>
    </v-fade-transition>
  </div>
</template>

<script lang="ts">
// Libraries
import axios from '@/axios-auth'
import { mapState, mapGetters } from 'vuex'
import { BAD_REQUEST, PAYMENT_REQUIRED } from 'http-status-codes'

// Components
import CodDate from '@/components/StandaloneDirectorChange/CODDate.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { SummaryDirectors, SummaryCertify, SummaryStaffPayment } from '@/components/common'

// Dialog Components
import { ConfirmDialog, PaymentErrorDialog, ResumeErrorDialog, SaveErrorDialog } from '@/components/dialogs'

// Mixins
import { EntityFilterMixin, ResourceLookupMixin } from '@/mixins'

// Enums
import { EntityTypes, FilingCodes } from '@/enums'

// Constants
import { CEASED, APPOINTED, ADDRESSCHANGED, NAMECHANGED } from '@/constants'

export default {
  name: 'StandaloneDirectorsFiling',

  components: {
    CodDate,
    Directors,
    SummaryDirectors,
    SummaryCertify,
    SummaryStaffPayment,
    SbcFeeSummary,
    Certify,
    StaffPayment,
    ConfirmDialog,
    PaymentErrorDialog,
    ResumeErrorDialog,
    SaveErrorDialog
  },

  mixins: [EntityFilterMixin, ResourceLookupMixin],

  data () {
    return {
      allDirectors: [],
      filingData: [],
      resumeErrorDialog: false,
      saveErrorDialog: false,
      paymentErrorDialog: false,
      earliestDateToSet: 'your last filing',
      inFilingReview: false,
      isCertified: false,
      certifiedBy: '',
      certifyFormValid: false,
      directorFormValid: true,
      directorEditInProgress: false,
      filingId: null,
      loadingMessage: 'Loading...', // initial generic message
      saving: false,
      savingResuming: false,
      filingPaying: false,
      haveChanges: false,
      saveErrors: [],
      saveWarnings: [],
      initialCODDate: '',
      codDate: null,
      codDateValid: false,
      complianceDialogMsg: null,

      // properties for Staff Payment component
      routingSlipNumber: null,
      staffPaymentFormValid: false,
      totalFee: 0,

      // enums
      EntityTypes,
      FilingCodes
    }
  },

  computed: {
    ...mapState(['currentDate', 'entityType', 'entityName', 'entityIncNo', 'entityFoundingDate']),

    ...mapGetters(['isRoleStaff']),

    validated () {
      const staffPaymentValid = (!this.isRoleStaff || !this.isPayRequired || this.staffPaymentFormValid)
      const filingDataValid = (this.filingData.length > 0)

      return (staffPaymentValid && this.certifyFormValid && this.directorFormValid && filingDataValid &&
        !this.directorEditInProgress && this.codDateValid)
    },

    busySaving () {
      return (this.saving || this.savingResuming || this.filingPaying)
    },

    isSaveButtonEnabled () {
      return (this.directorFormValid && this.filingData.length > 0 && !this.directorEditInProgress && this.codDateValid)
    },

    payAPIURL () {
      return sessionStorage.getItem('PAY_API_URL')
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

    // NB: filing id of 0 means "new"
    // otherwise it's a draft filing id
    this.filingId = this.$route.params.id

    // if tombstone data isn't set, route to home
    if (!this.entityIncNo || (this.filingId === undefined)) {
      this.$router.push('/')
    } else if (this.filingId > 0) {
      // resume draft filing
      this.loadingMessage = `Resuming Your Director Change`
      this.fetchChangeOfDirectors()
    } else {
      // else just load new page
      this.loadingMessage = `Preparing Your Director Change`
      this.initialCODDate = this.currentDate.split('/').join('-')
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
      'You have unsaved changes in your Change of Directors. Do you want to exit your filing?',
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

      let changeOfDirectors = null

      const header = {
        header: {
          name: 'changeOfDirectors',
          certifiedBy: this.certifiedBy || '',
          email: 'no_one@never.get',
          date: this.currentDate,
          effectiveDate: this.codDate + 'T00:00:00+00:00'
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

      if (this.isDataChanged('OTCDR') || this.isDataChanged('OTFDR')) {
        changeOfDirectors = {
          changeOfDirectors: {
            directors: this.allDirectors
          }
        }
      }

      const filingData = {
        filing: Object.assign(
          {},
          header,
          business,
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
        await axios.put(url, filingData).then(res => {
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
        await axios.post(url, filingData).then(res => {
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

    fetchChangeOfDirectors () {
      const url = this.entityIncNo + '/filings/' + this.filingId
      axios.get(url).then(response => {
        if (response && response.data) {
          const filing = response.data.filing
          try {
            // verify data
            if (!filing) throw new Error('missing filing')
            if (!filing.header) throw new Error('missing header')
            if (!filing.business) throw new Error('missing business')
            if (filing.header.name !== 'changeOfDirectors') throw new Error('invalid filing type')
            if (filing.business.identifier !== this.entityIncNo) throw new Error('invalid business identifier')
            if (filing.business.legalName !== this.entityName) throw new Error('invalid business legal name')

            this.certifiedBy = filing.header.certifiedBy
            this.routingSlipNumber = filing.header.routingSlipNumber

            if (filing.header.effectiveDate) {
              this.initialCODDate = filing.header.effectiveDate.slice(0, 10)
            } else {
              // eslint-disable-next-line no-console
              console.error('fetchChangeOfDirectors() error = missing Effective Date')
            }

            const changeOfDirectors = filing.changeOfDirectors
            if (changeOfDirectors) {
              if (changeOfDirectors.directors && changeOfDirectors.directors.length > 0) {
                if (this.$refs.directorsList && this.$refs.directorsList.setAllDirectors) {
                  this.$refs.directorsList.setAllDirectors(changeOfDirectors.directors)
                }

                // add filing code for paid changes
                if (changeOfDirectors.directors.filter(
                  director => this.hasAction(director, CEASED) ||
                    this.hasAction(director, APPOINTED)
                ).length > 0) {
                  this.toggleFiling('add', 'OTCDR')
                }

                // add filing code for free changes
                if (changeOfDirectors.directors.filter(
                  director => this.hasAction(director, NAMECHANGED) ||
                    this.hasAction(director, ADDRESSCHANGED)
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
          } catch (err) {
            // eslint-disable-next-line no-console
            console.log(`fetchData() error - ${err.message}, filing =`, filing)
            this.resumeErrorDialog = true
          }
        }
      }).catch(error => {
        // eslint-disable-next-line no-console
        console.error('fetchData() error =', error)
        this.resumeErrorDialog = true
      })
    },

    resetErrors () {
      this.saveErrorDialog = false
      this.saveErrors = []
      this.saveWarnings = []
    },

    hasAction (director, action) {
      if (director.actions.indexOf(action) >= 0) return true
      else return false
    },

    /**
      * Local method to change the state of the view and render the summary content
      * & relocate window to the top of page
      */
    showSummary (): void {
      this.inFilingReview = true
      document.body.scrollTop = 0 // For Safari
      document.documentElement.scrollTop = 0 // For Chrome, Firefox and IE
    },

    /**
     * Local method to change the state of the view and render the editable directors list
     */
    returnToFiling (): void {
      this.inFilingReview = false
      document.body.scrollTop = 0 // For Safari
      document.documentElement.scrollTop = 0 // For Chrome, Firefox and IE
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

  watch: {
    isCertified (val) {
      this.haveChanges = true
    },

    certifiedBy (val) {
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

// Save & Filing Buttons
#standalone-directors-buttons-container,
#standalone-directors-buttons-container-review {
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

  #cod-cancel-btn {
    margin-left: 0.5rem;
  }
}

.complianceDialogMsg {
  font-size: 1rem;
  color: $gray7;
}
</style>
