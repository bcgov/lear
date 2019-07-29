<template>
  <div>
    <v-dialog  v-model="dialog" width="50rem">
      <v-card>
        <v-card-title>Error</v-card-title>

        <v-card-text>
          An error occured during processing. Please try later
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" flat @click="navigateToDashboard">
           Back to My Dashboard
          </v-btn>
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
            <h1 id="AR-header">Directors - As of {{ lastFilingDate }}</h1>
          </header>

          <div>
            <!-- Director Information -->
            <section>
              <header>
                <h2 id="AR-step-3-header">xxx</h2>
              </header>
                <Directors @directorsChange="directorsChangeEventHandler" ref="directorsList" :asOfDate="currentDate" />
            </section>
          </div>
        </article>

        <aside>
          <affix relative-element-selector="#standalone-directors-article" :offset="{ top: 120, bottom: 40 }">
            <sbc-fee-summary v-bind:filingData="[...filingData]" v-bind:payURL="payAPIURL"/>
          </affix>
        </aside>
      </v-container>

      <v-container id="submit-container" class="pt-0">
        <div class="filing-buttons">
          <v-btn
            id="cod-pay-btn"
            color="primary"
            large
            @click="submit">
            File &amp; Pay
          </v-btn>
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
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapActions, mapGetters } from 'vuex'

export default {
  name: 'StandaloneDirectorsFiling',

  components: {
    Directors,
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
      lastFilingDate: 'something' // TODO
    }
  },

  computed: {
    ...mapState(['noAGM', 'regOffAddrChange',
      'validated', 'currentDate', 'corpNum',
      'entityName', 'entityIncNo', 'entityFoundingDate', 'currentARStatus',
      'addressesFormValid', 'directorFormValid'])

  },

  mounted () {
    // if tombstone data isn't set, redirect to home
    if (!this.corpNum) {
      this.$router.push('/')
    } else {
      // load initial data
      // TODO - anything here?
    }
  },

  methods: {
    ...mapActions(['setDirectorFormValid']),

    directorsChangeEventHandler (val) {
      this.directorsChange = val
    },

    submit () {
      let changeOfDirectors = null

      const header = {
        header: { name: 'changeOfDirectors', date: this.currentDate }
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
            certifiedBy: 'Full Name',
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

      // Temp fix Added to remove cors error while invoking mock endpoint.
      // To be removed when the API is in place
      let config = {
        headers: {
          'Content-Type': 'text/plain'
        }
      }

      axios.post(this.corpNum + '/filings', filingData, config).then(res => {
        let payRequestId:String = res.data.filing.header.paymentToken
        payRequestId = '189'
        let returnURL = window.location.origin + '/standalone-directors?pay_id=' + payRequestId
        let authStub:string = this.authURL
        if (!(authStub.endsWith('/'))) {
          authStub = authStub + '/'
        }
        let payURL = authStub + 'makepayment/' + payRequestId + '/' + encodeURIComponent(returnURL)
        window.location.href = payURL
      }).catch((error) => {
        // TODO : To Decide how and where to display the error message from API
        console.log(error)
        this.dialog = true
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
    }
  },

  watch: {

    directorsChange: function (val) {
      // when directors change, update filing data
      console.log('Standalone Directors, directorsChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTCDR')
      } else {
        this.toggleFiling('remove', 'OTCDR')
      }
    },

    directorFormValid (val) {
      this.setValidateFlag()
    },

    filingData: function (val) {
      console.log('StandaloneDirectorsFiling, filingData =', val)
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

// Filing Buttons
.filing-buttons
  padding-top: 2rem;
  border-top: 1px solid $gray5;
  text-align: right;

  .v-btn + .v-btn
    margin-left: 0.5rem;
</style>
