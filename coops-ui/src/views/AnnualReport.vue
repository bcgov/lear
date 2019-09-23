<template>
  <div>
    <ConfirmDialog ref="confirm" />

    <ResumeErrorDialog
      :dialog="resumeErrorDialog"
      @exit="navigateToDashboard"
    />

    <SaveErrorDialog
      :dialog="saveErrorDialog"
      :disableRetry="filingPaying"
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
            <p>Select your Annual General Meeting (AGM) date, and verify or change your Registered office address
              and List of Directors as of your AGM.</p>
          </header>

          <div v-if="isAnnualReportEditable">
            <!-- Annual General Meeting Date -->
            <section>
              <header>
                <h2 id="AR-step-1-header">1. Annual General Meeting Date</h2>
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
                @allDirectors="allDirectors=$event"
                @directorFormValid="directorFormValid=$event"
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
          <v-tooltip top color="#3b6cff">
            <v-btn
              slot="activator"
              v-if="isAnnualReportEditable"
              id="ar-file-pay-btn"
              color="primary"
              large
              :depressed="isRoleStaff"
              :ripple="!isRoleStaff"
              :disabled="!validated || filingPaying"
              :loading="filingPaying"
              @click="onClickFilePay">
              File &amp; Pay
            </v-btn>
            <span v-if="isRoleStaff">Staff are not allowed to file.</span>
            <span v-else>Ensure all of your information is entered correctly before you File &amp; Pay.<br>
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
import { mapState, mapGetters } from 'vuex'
import { BAD_REQUEST, PAYMENT_REQUIRED } from 'http-status-codes'
import Certify from '@/components/AnnualReport/Certify.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import PaymentErrorDialog from '@/components/AnnualReport/PaymentErrorDialog.vue'
import ResumeErrorDialog from '@/components/AnnualReport/ResumeErrorDialog.vue'
import SaveErrorDialog from '@/components/AnnualReport/SaveErrorDialog.vue'
import DateMixin from '@/mixins/date-mixin'

export default {
  name: 'AnnualReport',

  mixins: [DateMixin],

  components: {
    AGMDate,
    RegisteredOfficeAddress,
    Directors,
    Certify,
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

      // properties for Certify component
      certifiedBy: '',
      isCertified: false,
      certifyFormValid: null,

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
      saveWarnings: []
    }
  },

  computed: {
    ...mapState(['currentDate', 'ARFilingYear', 'lastAgmDate', 'entityName',
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
      return this.agmDateValid && this.addressesFormValid && this.directorFormValid && this.certifyFormValid
    },

    isSaveButtonEnabled () {
      return this.agmDateValid && this.addressesFormValid && this.directorFormValid
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
      'Save Your Changes to Your Annual Report?',
      'You have unsaved changes in your Annual Report. Do you want to save your changes?',
      { width: '40rem', persistent: true, yes: 'Save', no: 'Don\'t save' }
    ).then(async (confirm) => {
      // if we get here, Yes or No was clicked
      if (confirm) {
        await this.onClickSave()
      } else {
        this.haveChanges = false
      }
      next()
    }).catch(() => {
      // if we get here, Cancel was clicked
      next(false)
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
                this.toggleFiling('add', 'OTCDR')
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

    async onClickSave () {
      this.saving = true
      const filing = await this.saveFiling(true)
      if (filing) {
        this.filingId = +filing.header.filingId
      }
      this.saving = false
    },

    async onClickSaveResume () {
      this.savingResuming = true
      const filing = await this.saveFiling(true)
      // on success, route to Home URL
      if (filing) {
        this.$router.push('/')
      }
      this.savingResuming = false
    },

    async onClickFilePay () {
      // staff are not allowed to file
      if (this.isRoleStaff) return false

      this.filingPaying = true
      const filing = await this.saveFiling(false)
      // on success, redirect to Pay URL
      if (filing && filing.header) {
        const origin = window.location.origin || ''
        const filingId = +filing.header.filingId
        const returnURL = encodeURIComponent(origin + '/dashboard?filing_id=' + filingId)
        let authStub: string = sessionStorage.getItem('AUTH_URL') || ''
        if (!(authStub.endsWith('/'))) { authStub += '/' }
        const paymentToken = filing.header.paymentToken
        const payURL = authStub + 'makepayment/' + paymentToken + '/' + returnURL
        // assume Pay URL is always reachable
        window.location.assign(payURL)
      }
      this.filingPaying = false
      return true
    },

    async saveFiling (isDraft) {
      this.saveErrorDialog = false
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

      if (this.isDataChanged('OTCDR')) {
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
        this.filingData.push({ filingTypeCode: filing, entityType: 'CP' })
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
</style>
