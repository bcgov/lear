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

    <div id="annual-report" ref="annualReport">
      <!-- Initial Page Load Transition -->
      <div class="loading-container fade-out">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">Preparing Your {{ ARFilingYear }} Annual Report</div>
        </div>
      </div>

      <v-container id="annual-report-container" class="view-container">
        <article id="annual-report-article" :class="this.agmDate ? 'agm-date-selected' : 'no-agm-date-selected'">
          <header>
            <h1 id="AR-header">File {{ ARFilingYear }} Annual Report -
              <span style="font-style: italic">{{ reportState }}</span>
            </h1>
            <p>Select your Annual General Meeting (AGM) date, and verify or change your Registered office address
              and List of Directors as of your AGM.</p>
          </header>

          <!-- proof of concept for JSON schema validation -->
          <section>
            <header>
              <h2 id="AR-step-header">JSON Schema Validation Example</h2>
            </header>
            <div class="form__row three-column">
              <div class="item" v-if="$schema && !$schema.then">
                <v-text-field box
                  ref="firstName"
                  label="First Name"
                  v-model.lazy="$v.schema.firstName.$model"
                  hide-details
                  @blur="$v.schema.firstName.$touch()"
                  :class="{'red-border': $v.schema.firstName.$error}">
                </v-text-field>
                <!-- these errors could also be their own dynamic component (based on schema) -->
                <!-- or use 'vuelidate-error-extractor' package to display error messages -->
                <p class="validation-error mb-0"
                  v-if="$v.schema.firstName.$dirty && !$v.schema.firstName.required">
                  First Name is required</p>
                <p class="validation-error mb-0"
                  v-if="$v.schema.firstName.$dirty && !$v.schema.firstName.schemaRequired">
                  First Name property must be present</p>
                <p class="validation-error mb-0"
                  v-if="$v.schema.firstName.$dirty && !$v.schema.firstName.schemaMaxLength">
                  First Name must have at most {{$v.schema.firstName.$params.schemaMaxLength.max}}
                  character(s).</p>
              </div>

              <div class="item director-initial" v-if="$schema && !$schema.then">
                <v-text-field box
                  ref="middleInitial"
                  label="Initial"
                  v-model="$v.schema.middleInitial.$model"
                  hide-details
                  @blur="$v.schema.middleInitial.$touch()"
                  :class="{'red-border': $v.schema.middleInitial.$error}">
                </v-text-field>
                <p class="validation-error mb-0"
                  v-if="$v.schema.middleInitial.$dirty && !$v.schema.middleInitial.schemaMaxLength">
                  Middle Initial must have at most {{$v.schema.middleInitial.$params.schemaMaxLength.max}}
                  character(s).</p>
              </div>

              <div class="item" v-if="$schema && !$schema.then">
                <v-text-field box
                  ref="lastName"
                  label="Last Name"
                  v-model="$v.schema.lastName.$model"
                  hide-details
                  @blur="$v.schema.lastName.$touch()"
                  :class="{'red-border': $v.schema.lastName.$error}">
                </v-text-field>
                <p class="validation-error mb-0"
                  v-if="$v.schema.lastName.$dirty && !$v.schema.lastName.required">
                  Last Name is required</p>
                <p class="validation-error mb-0"
                  v-if="$v.schema.lastName.$dirty && !$v.schema.lastName.schemaRequired">
                  Last Name property must be present</p>
                <p class="validation-error mb-0"
                  v-if="$v.schema.lastName.$dirty && !$v.schema.lastName.schemaMaxLength">
                  Last Name must have at most {{$v.schema.lastName.$params.schemaMaxLength.max}}
                  character(s).</p>
              </div>
            </div>

            <v-btn @click="onValidateClick" color="primary">Validate</v-btn>
            <v-btn @click="onResetClick" color="primary">Reset</v-btn>
          </section>

          <div v-if="isAnnualReportEditable">
            <!-- Annual General Meeting Date -->
            <section>
              <header>
                <h2 id="AR-step-1-header">1. Annual General Meeting Date</h2>
              </header>
              <v-card flat id="AR-step-1-container">
                <AGMDate/>
              </v-card>
            </section>

            <!-- Addresses -->
            <section>
              <header>
                <h2 id="AR-step-2-header">2. Registered Office Addresses
                  <span class="agm-date">(as of {{ ARFilingYear }} Annual General Meeting)</span>
                </h2>
                <p>Verify or change your Registered Office Addresses.</p>
              </header>
              <v-card flat id="AR-step-2-container">
                <RegisteredOfficeAddress ref="registeredAddress"/>
              </v-card>
            </section>

            <!-- Director Information -->
            <section>
              <header>
                <h2 id="AR-step-3-header">3. Directors</h2>
                <p>Tell us who was elected or appointed and who ceased to be a director at your
                  {{ ARFilingYear }} AGM.</p>
              </header>
              <!-- <v-card flat id="AR-step-3-container"> -->
                <Directors @directorsChange="directorsChangeEventHandler" ref="directorsList"/>
              <!-- </v-card> -->
            </section>
          </div>
          <div v-else>
           <!-- <ARComplete/> -->
          </div>
        </article>

        <aside>
          <affix relative-element-selector="#annual-report-article" :offset="{ top: 120, bottom: 40 }">
            <sbc-fee-summary v-bind:filingData="[...filingData]" />
          </affix>
        </aside>
      </v-container>

      <v-container id="submit-container" class="pt-0">
        <div class="ar-filing-buttons">
          <v-btn
            v-if="isAnnualReportEditable"
            id="ar-pay-btn"
            color="primary"
            large
            :disabled="!validated"
            @click="submit">
            File &amp; Pay
          </v-btn>
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
// import ARComplete from '@/components/AnnualReport/ARComplete.vue'
import { Affix } from 'vue-affix'
import SbcFeeSummary from 'sbc-common-components/src/components/SbcFeeSummary.vue'
import { mapState, mapActions, mapGetters } from 'vuex'
import { required } from 'vuelidate/lib/validators'

export default {
  name: 'AnnualReport',

  components: {
    AGMDate,
    RegisteredOfficeAddress,
    Directors,
    // ARComplete,
    SbcFeeSummary,
    Affix
  },

  data () {
    return {
      // NB: 'schema' object is automatically added
      schemaValidations: null,
      baseUrl: process.env.BASE_URL,
      showLoading: false,
      loadingMsg: 'Redirecting to PayBC to Process Your Payment',
      directorsChange: false,
      filingData: [],
      dialog: false
    }
  },

  validations () {
    // additional validation object to apply 'required' validator
    // see creation below
    return { schema: { ...this.schemaValidations } }
  },

  computed: {
    ...mapState(['agmDate', 'noAGM', 'regOffAddrChange',
      'validated', 'currentDate', 'ARFilingYear', 'corpNum', 'lastAgmDate',
      'entityName', 'entityIncNo', 'entityFoundingDate', 'currentARStatus']),

    ...mapGetters(['isAnnualReportEditable', 'reportState'])
  },

  // definition of schema
  // functionally equal to 'data.schema' and 'validations' properties
  // ref: https://github.com/mokkabonna/vue-vuelidate-jsonschema
  schema: [
    // load schema on module require (ie, synchronously)
    // axios.get(this.appBaseURL + '/schemas/person.json')
    // TODO: get appBaseURL before this runs
    axios.get('http://localhost:8080/schemas/person.json')
      .then(response => {
        return response.data
      })
      .catch(error => {
        console.log('error getting person schema: ', error)
      })
  ],

  // hard-coded schema example
  // we could also load the schema using import statement
  // schema: {
  //   'definitions': {},
  //   '$schema': 'http://json-schema.org/draft-07/schema#',
  //   '$id': 'https://bcrs.gov.bc.ca/.well_known/schemas/person',
  //   'type': 'object',
  //   'title': 'The Person Schema',
  //   'properties': {
  //     'firstName': {
  //       'type': 'string',
  //       'maxLength': 5
  //     },
  //     'middleInitial': {
  //       'type': 'string',
  //       'maxLength': 1
  //     },
  //     'lastName': {
  //       'type': 'string',
  //       'maxLength': 5
  //     }
  //   },
  //   'required': [
  //     'firstName',
  //     'lastName'
  //   ]
  // },

  mounted () {
    console.log('Annual Report is mounted')
    // if tombstone data isn't set, redirect to home
    if (!this.corpNum || !this.ARFilingYear) {
      this.$router.push('/')
    } else {
      // load initial data
      // TODO - anything here?
    }
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setValidated']),

    onValidateClick () {
      // make all controls 'dirty'
      // (or could call $touch() for parent model)
      Object.keys(this.schema).forEach(key => this.$v.schema[key].$touch())
    },

    onResetClick () {
      // make all controls 'untouched'
      // (or could call $reset() for parent model)
      Object.keys(this.schema).forEach(key => this.$v.schema[key].$reset())
    },

    directorsChangeEventHandler (val) {
      this.directorsChange = val
    },

    submit () {
      let changeOfDirectors = null
      let changeOfAddress = null

      const header = {
        header: { name: 'annual_report', date: this.currentDate }
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
          certifiedBy: 'full name',
          email: 'no_one@never.get'
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

      if (this.isDataChanged('OTADD')) {
        changeOfAddress = {
          changeOfAddress: {
            certifiedBy: 'Full Name',
            email: 'no_one@never.get',
            deliveryAddress: this.$refs.registeredAddress.getDeliveryAddress(),
            mailingAddress: this.$refs.registeredAddress.getMailingAddress()
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

      // Temp fix Added to remove cors error while invoking mock endpoint.
      // To be removed when the API is in place
      let config = {
        headers: {
          'Content-Type': 'text/plain'
        }
      }

      axios.post(this.corpNum + '/filings', filingData, config).then(res => {
        let payRequestId = res.data.filing.header.paymentToken
        payRequestId = '189'// To be removed
        let returnURL = window.location.origin + '/AnnualReport?pay_id=' + payRequestId
        let payURL = this.authURL + 'makepayment/' + payRequestId + '/' + encodeURIComponent(returnURL)
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
    // TODO - what to do if Corp Num ever changes?
    // corpNum (val) {
    //   console.log('AnnualReport, corpNum =', val)
    // },

    schema: function (val) {
      // 'vue-vuelidate-jsonschema' does not apply the 'required' validator in vuelidate
      // so, create additional schema validation object
      // ie, convert schemaRequired -> required
      const temp = {}
      Object.keys(val)
        .filter(key => this.$v.schema[key].schemaRequired)
        .forEach(key => { temp[key] = { required } })
      this.schemaValidations = temp
    },

    agmDate (val) {
      // when AGM Date changes, update filing data
      console.log('AnnualReport, agmDate =', val)
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        if (!this.noAGM) this.toggleFiling('remove', 'OTANN')
      }
      this.setValidated(Boolean(this.noAGM || this.agmDate))
    },

    noAGM (val) {
      // when No AGM changes, update filing data
      console.log('AnnualReport, noAGM =', val)
      if (val) {
        this.toggleFiling('add', 'OTANN')
      } else {
        this.toggleFiling('remove', 'OTANN')
      }
      this.setValidated(Boolean(this.noAGM || this.agmDate))
    },

    regOffAddrChange: function (val) {
      // when addresses change, update filing data
      console.log('AnnualReport, regOffAddrChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTADD')
      } else {
        this.toggleFiling('remove', 'OTADD')
      }
    },

    directorsChange: function (val) {
      // when directors change, update filing data
      console.log('AnnualReport, directorsChange =', val)
      if (val) {
        this.toggleFiling('add', 'OTCDR')
      } else {
        this.toggleFiling('remove', 'OTCDR')
      }
    },

    validated (val) {
      console.log('AnnualReport, validated =', val)
    },

    filingData: function (val) {
      console.log('AnnualReport, filingData =', val)
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

.form__row.three-column
  display flex
  flex-flow row nowrap
  align-items stretch
  margin-right -0.5rem
  margin-left -0.5rem

  .item
    flex 1 1 auto
    flex-basis 0
    margin-right 0.5rem
    margin-left 0.5rem

.director-initial
  max-width 6rem

.red-border
  border 1px solid red

.validation-error
  color red

#AR-step-header,
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
.ar-filing-buttons
  padding-top: 2rem;
  border-top: 1px solid $gray5;
  text-align: right;

  .v-btn + .v-btn
    margin-left: 0.5rem;
</style>
