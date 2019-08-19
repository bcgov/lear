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

    <div id="standalone-directors" ref="standaloneDirectors">
      <!-- Initial Page Load Transition -->
      <div class="loading-container fade-out">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">Preparing Your Filing</div>
        </div>
      </div>

      <v-container id="standalone-directors-container" class="view-container">
        <article id="standalone-directors-article">
          <header>
            <h1 id="filing-header">Change of Directors</h1>

            <v-alert type="info" :value="true" icon="info" outline style="background-color: white;">
              Director changes can be made as far back as {{ lastFilingDate }}.
            </v-alert>
          </header>

          <div>
            <!-- Director Information -->
            <section>
              <Directors ref="directorsList"
                @directorsChange="directorsChange"
                @lastFilingDate="lastFilingDate=$event"
                @directorFormValid="directorFormValid=$event"
                :asOfDate="currentDate"
                />
            </section>

            <!-- Certify -->
            <section>
              <header>
                <h2 id="AR-step-4-header">Certify Correct</h2>
                <p>Enter the name of the current director, officer, or lawyer submitting this Annual Report.</p>
              </header>
              <Certify @certifyChange="changeCertifyData" @certifiedBy="certifiedBy=$event" ref="certifyClause"/>
            </section>
          </div>
        </article>

        <aside>
          <affix relative-element-selector="#standalone-directors-article" :offset="{ top: 120, bottom: 40 }">
            <sbc-fee-summary v-bind:filingData="[...filingData]" v-bind:payURL="payAPIURL"/>
          </affix>
        </aside>
      </v-container>

      <v-container id="buttons-container" class="list-item">
        <div class="buttons-left">
          <v-btn id="cod-save-btn" large
            :disabled="!saveButtonEnabled || saving"
            :loading="saving"
            @click="onClickSave">
            Save
          </v-btn>
          <v-btn id="cod-save-resume-btn" large
            :disabled="!saveButtonEnabled || savingResuming"
            :loading="savingResuming"
            @click="onClickSaveResume">
            Save &amp; Resume Later
          </v-btn>
        </div>

        <div class="buttons-right">
          <v-tooltip bottom>
            <v-btn
              slot="activator"
              id="cod-file-pay-btn"
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
            id="cod-cancel-btn"
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
import Directors from '@/components/AnnualReport/Directors.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapActions } from 'vuex'
import { PAYMENT_REQUIRED } from 'http-status-codes'

export default {
  name: 'StandaloneDirectorsFiling',

  components: {
    Directors,
    SbcFeeSummary,
    Affix,
    Certify
  },

  data () {
    return {
      loadingMsg: 'Redirecting to PayBC to Process Your Payment',
      filingData: [],
      resumeErrorDialog: false,
      saveErrorDialog: false,
      paymentErrorDialog: false,
      lastFilingDate: 'your last filing',
      certifyChange: false,
      certifiedBy: null,
      directorFormValid: true,
      saving: false,
      savingResuming: false,
      filingPaying: false
    }
  },

  computed: {
    ...mapState(['currentDate', 'corpNum', 'entityName', 'entityIncNo', 'entityFoundingDate']),

    validated () {
      return this.certifyChange && this.directorFormValid && this.filingData.length > 0
    },

    saveButtonEnabled () {
      return this.directorFormValid && this.filingData.length > 0
    }
  },

  mounted () {
    // if tombstone data isn't set, route to home
    if (!this.corpNum) {
      this.$router.push('/')
    }

    // if loading from draft...
    this.filingId = this.$route.params.id
    if (this.filingId > '0') {
      this.fetchChangeOfDirectors()
    }
  },

  methods: {
    directorsChange (val) {
      // when directors change, update filing data
      if (val) {
        this.toggleFiling('add', 'OTCDR')
      } else {
        this.toggleFiling('remove', 'OTCDR')
      }
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
      // on success, redirect to Home URL
      if (filing) {
        const homeURL = window.location.origin || ''
        window.location.assign(homeURL)
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
        // TODO: first check if pay UI is reachable, else display modal dialog
        window.location.assign(payURL)
      } else {
        console.log('onClickFilePay() error - invalid filing =', filing)
      }
      this.filingPaying = false
    },

    async saveFiling (isDraft) {
      this.saveErrorDialog = false
      let changeOfDirectors = null

      const header = {
        header: {
          name: 'changeOfDirectors',
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

      if (this.isDataChanged('OTCDR')) {
        changeOfDirectors = {
          changeOfDirectors: {
            certifiedBy: this.certifiedBy || '',
            email: 'no_one@never.get',
            directors: this.$refs.directorsList.getAllDirectors()
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

    changeCertifyData (val) {
      this.certifyChange = val
    },

    fetchChangeOfDirectors () {
      const url = this.corpNum + '/filings/' + this.filingId
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
          } catch (err) {
            console.log(`fetchData() error - ${err.message}, filing =`, filing)
            this.resumeErrorDialog = true
          }
        }
      }).catch(error => {
        console.error('fetchData() error =', error)
        this.resumeErrorDialog = true
      })
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
