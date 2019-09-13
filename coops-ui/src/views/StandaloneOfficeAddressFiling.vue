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
            <h1 id="filing-header">Change of Office Addresses</h1>
          </header>

          <!-- Registered Office Addresses -->
          <section>
            <RegisteredOfficeAddress
              :changeButtonDisabled="false"
              :legalEntityNumber="entityIncNo"
              :addresses.sync="addresses"
              @modified="officeModifiedEventHandler($event)"
              @valid="officeAddressFormValid = $event" />
          </section>

          <!-- Certify -->
          <section>
            <header>
              <h2 id="AR-step-4-header">Certify Correct</h2>
              <p>Enter the name of the current director, officer, or lawyer submitting this Annual Report.</p>
            </header>
            <Certify
              :isCertified.sync="isCertified"
              :certifiedBy.sync="certifiedBy" />
          </section>
        </article>

        <aside>
          <affix relative-element-selector="#standalone-office-address-article" :offset="{ top: 120, bottom: 40 }">
            <sbc-fee-summary v-bind:filingData="[...filingData]" v-bind:payURL="payAPIURL"/>
          </affix>
        </aside>
      </v-container>

      <v-container id="buttons-container" class="list-item">
        <div class="buttons-left">
          <v-btn id="coa-save-btn" large
            :disabled="!saveAsDraftEnabled || saving"
            :loading="saving"
            @click="onClickSave">
            Save
          </v-btn>
          <v-btn id="coa-save-resume-btn" large
            :disabled="!saveAsDraftEnabled || savingResuming"
            :loading="savingResuming"
            @click="onClickSaveResume">
            Save &amp; Resume Later
          </v-btn>
        </div>

        <div class="buttons-right">
          <v-tooltip top color="#3b6cff">
            <v-btn
              slot="activator"
              id="coa-file-pay-btn"
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
            id="coa-cancel-btn"
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
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapGetters } from 'vuex'
import { PAYMENT_REQUIRED, BAD_REQUEST } from 'http-status-codes'
import Certify from '@/components/AnnualReport/Certify.vue'
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
      officeAddressFormValid: true,
      saving: false,
      savingResuming: false,
      filingPaying: false,
      haveChanges: false,
      saveErrors: [],
      saveWarnings: []
    }
  },

  computed: {
    ...mapState(['currentDate', 'entityName', 'entityIncNo', 'entityFoundingDate']),

    ...mapGetters(['isRoleStaff']),

    validated () {
      return (this.isCertified && this.officeAddressFormValid && this.filingData.length > 0)
    },

    saveAsDraftEnabled () {
      return (this.officeAddressFormValid && this.filingData.length > 0)
    },

    payAPIURL () {
      return sessionStorage.getItem('PAY_API_URL')
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
      'Save Your Changes to Your Change of Office Addresses?',
      'You have unsaved changes in your Change of Office Addresses. Do you want to save your changes?',
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
      // on success, redirect to Home URL
      if (filing) {
        const homeURL = window.location.origin || ''
        window.location.assign(homeURL)
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
        // TODO: first check if pay UI is reachable, else display modal dialog
        window.location.assign(payURL)
      }
      this.filingPaying = false
      return true
    },

    async saveFiling (isDraft) {
      this.saveErrorDialog = false
      let changeOfAddress = null

      const header = {
        header: {
          name: 'changeOfAddress',
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
    }
  },

  watch: {
    isCertified (val) {
      this.haveChanges = true
    },

    certifiedBy (val) {
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

#filing-header
  margin-bottom: 1.25rem;
  line-height: 2rem;
  letter-spacing: -0.01rem;
  font-size: 2rem;
  font-weight: 500;

.title-container
  margin-bottom: 0.5rem;

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
