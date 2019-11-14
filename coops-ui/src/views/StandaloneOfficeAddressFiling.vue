<template>
  <div>
    <!-- Dialogs -->
    <ConfirmDialog ref="confirm" />

    <ResumeErrorDialog
      :dialog="resumeErrorDialog"
      @exit="navigateToDashboard"
    />

    <SaveErrorDialog
      filing="Address Change"
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

    <div id="standalone-office-address" ref="standaloneOfficeAddress">
      <!-- Initial Page Load Transition -->
      <div class="loading-container fade-out">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">Preparing Your Filing</div>
        </div>
      </div>

      <v-container id="standalone-office-address-container" class="view-container">
        <article id="standalone-office-address-article">
          <header>
            <h1 id="filing-header">Address Change</h1>
          </header>

          <!-- Registered Office Addresses -->
          <section>
            <RegisteredOfficeAddress
              :changeButtonDisabled="false"
              :legalEntityNumber="entityIncNo"
              :addresses.sync="addresses"
              @modified="officeModifiedEventHandler($event)"
              @valid="officeAddressFormValid = $event"
            />
          </section>

          <!-- Certify -->
          <section>
            <header>
              <h2 id="AR-step-4-header">Certify Correct</h2>
              <p>Enter the name of the current director, officer, or lawyer submitting this Annual Report.</p>
            </header>
            <Certify
              :isCertified.sync="isCertified"
              :certifiedBy.sync="certifiedBy"
              @valid="certifyFormValid=$event"
            />
          </section>

          <!-- Staff Payment -->
          <section v-if="isRoleStaff && isPayRequired">
            <header>
              <h2 id="AR-step-5-header">Staff Payment</h2>
            </header>
            <StaffPayment
              :value.sync="routingSlipNumber"
              @valid="staffPaymentFormValid=$event"
            />
          </section>
        </article>

        <aside>
          <affix relative-element-selector="#standalone-office-address-article" :offset="{ top: 120, bottom: 40 }">
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
          <v-btn id="coa-save-btn" large
            :disabled="!saveAsDraftEnabled || busySaving"
            :loading="saving"
            @click="onClickSave"
          >
            Save
          </v-btn>
          <v-btn id="coa-save-resume-btn" large
            :disabled="!saveAsDraftEnabled || busySaving"
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
                id="coa-file-pay-btn"
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
            id="coa-cancel-btn"
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
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapGetters } from 'vuex'
import { PAYMENT_REQUIRED, BAD_REQUEST } from 'http-status-codes'
import Certify from '@/components/AnnualReport/Certify.vue'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import PaymentErrorDialog from '@/components/AnnualReport/PaymentErrorDialog.vue'
import ResumeErrorDialog from '@/components/AnnualReport/ResumeErrorDialog.vue'
import SaveErrorDialog from '@/components/AnnualReport/SaveErrorDialog.vue'

export default {
  name: 'StandaloneOfficeAddressFiling',

  components: {
    RegisteredOfficeAddress,
    SbcFeeSummary,
    Affix,
    Certify,
    StaffPayment,
    ConfirmDialog,
    PaymentErrorDialog,
    ResumeErrorDialog,
    SaveErrorDialog
  },

  data () {
    return {
      addresses: null,
      filingId: null,
      showLoading: false,
      filingData: [],
      resumeErrorDialog: false,
      saveErrorDialog: false,
      paymentErrorDialog: false,
      isCertified: false,
      certifiedBy: '',
      certifyFormValid: false,
      officeAddressFormValid: true,
      saving: false,
      savingResuming: false,
      filingPaying: false,
      haveChanges: false,
      saveErrors: [],
      saveWarnings: [],

      // properties for Staff Payment component
      routingSlipNumber: null,
      staffPaymentFormValid: false,
      totalFee: 0
    }
  },

  computed: {
    ...mapState(['currentDate', 'entityType', 'entityName', 'entityIncNo', 'entityFoundingDate']),

    ...mapGetters(['isRoleStaff']),

    validated () {
      const staffPaymentValid = (!this.isRoleStaff || !this.isPayRequired || this.staffPaymentFormValid)
      const filingDataValid = (this.filingData.length > 0)

      return (staffPaymentValid && this.certifyFormValid && this.officeAddressFormValid && filingDataValid)
    },

    busySaving () {
      return (this.saving || this.savingResuming || this.filingPaying)
    },

    saveAsDraftEnabled () {
      const filingDataValid = (this.filingData.length > 0)
      return (this.officeAddressFormValid && filingDataValid)
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
    }

    if (this.filingId > 0) {
      // resume draft filing
      this.fetchChangeOfAddressFiling()
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
      'You have unsaved changes in your Change of Office Addresses. Do you want to exit your filing?',
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
    formatAddress (address) {
      return {
        'actions': address.actions || [],
        'addressCity': address.addressCity || '',
        'addressCountry': address.addressCountry || '',
        'addressRegion': address.addressRegion || '',
        'addressType': address.addressType || '',
        'deliveryInstructions': address.deliveryInstructions || '',
        'postalCode': address.postalCode || '',
        'streetAddress': address.streetAddress || '',
        'streetAddressAdditional': address.streetAddressAdditional || ''
      }
    },

    fetchChangeOfAddressFiling () {
      const url = this.entityIncNo + '/filings/' + this.filingId
      axios.get(url).then(response => {
        if (response && response.data) {
          const filing = response.data.filing
          try {
            // verify data
            if (!filing) throw new Error('missing filing')
            if (!filing.header) throw new Error('missing header')
            if (!filing.business) throw new Error('missing business')
            if (filing.header.name !== 'changeOfAddress') throw new Error('invalid filing type')
            if (filing.business.identifier !== this.entityIncNo) throw new Error('invalid business identifier')
            if (filing.business.legalName !== this.entityName) throw new Error('invalid business legal name')

            this.certifiedBy = filing.header.certifiedBy
            this.routingSlipNumber = filing.header.routingSlipNumber

            // load Annual Report fields
            if (!filing.changeOfAddress) throw new Error('Missing change of address')

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

      let changeOfAddress = null

      const header = {
        header: {
          name: 'changeOfAddress',
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

      if (this.isDataChanged('OTADD') && this.addresses) {
        changeOfAddress = {
          changeOfAddress: {
            deliveryAddress: this.formatAddress(this.addresses['deliveryAddress']),
            mailingAddress: this.formatAddress(this.addresses['mailingAddress'])
          }
        }
      }

      const filingData = {
        filing: Object.assign(
          {},
          header,
          business,
          changeOfAddress
        )
      }

      if (this.filingId > 0) {
        // we have a filing id, so we are updating an existing filing
        let url = this.entityIncNo + '/filings/' + this.filingId
        if (isDraft) { url += '?draft=true' }
        let filing = null
        await axios.put(url, filingData).then(res => {
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
        await axios.post(url, filingData).then(res => {
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

#filing-header {
  margin-bottom: 1.25rem;
  line-height: 2rem;
  letter-spacing: -0.01rem;
}

.title-container {
  margin-bottom: 0.5rem;
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

  #coa-cancel-btn {
    margin-left: 0.5rem;
  }
}
</style>
