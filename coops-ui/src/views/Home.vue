<template>
  <div class="home">
    <v-app>
      <EntityInfo/>
      <AnnualReport/>
      <v-container>
<<<<<<< HEAD
        <v-btn v-if="filedDate == null" id='ar-pay-btn' color="blue" :disabled="!validated" @click="submit">Pay</v-btn>
        <v-btn v-else color="blue" id='ar-next-btn' :disabled="currentYear == ARFilingYear" @click="nextAR">Next</v-btn>
=======
        <v-btn color="blue" :disabled="!validated" @click="submit">Pay</v-btn>
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
      </v-container>
    </v-app>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
<<<<<<< HEAD
import axios from '@/axios-auth.ts'
import EntityInfo from '@/components/EntityInfo.vue'
import AnnualReport from '@/components/AnnualReport.vue'
=======
import axios from 'axios'
import EntityInfo from '@/components/EntityInfo.vue'
import AnnualReport from '@/components/AnnualReport.vue'
import Keycloak from '../assets/js/keycloak.js'
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST

export default {
  name: 'Home.vue',
  components: {
    EntityInfo,
    AnnualReport
  },
<<<<<<< HEAD
  data () {
    return {
      lastARJson: null,
      entityInfoJson: null
    }
  },
=======
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
<<<<<<< HEAD
    filedDate () {
      return this.$store.state.filedDate
    },
    validated () {
      return this.$store.state.validated
    },
    currentYear () {
      return this.$store.state.currentDate.substring(0, 4)
    },
    ARFilingYear () {
      return this.$store.state.ARFilingYear
    }
  },
  mounted () {
    var today = new Date()
    this.$store.state.currentDate = today.getFullYear() + '-' + ('0' + (+today.getMonth() + 1)).slice(-2) + '-' +
      ('0' + today.getDate()).slice(-2)

    if (this.ARFilingYear == null && this.corpNum != null) {
      this.getARInfo(this.corpNum)
      this.getEntityInfo(this.corpNum)
    }
  },
  methods: {
    getARInfo (corpNum) {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // when calling the api make sure this url is for most recent AR - stub specifies 2017 + add token in header
      var url = corpNum + '/filings/annual_report?year=2017'
      axios.get(url).then(response => {
        this.lastARJson = response.data
        this.setARInfo()
      }).catch(error => console.log('getARInfo ERROR: ' + error + ' ' + axios.get))
    },
    setARInfo () {
      var lastARYear = this.lastARJson.filing.annual_report.annual_general_meeting_date.substring(0, 4)
      var currentYear = (new Date()).getFullYear() + ''
      if (lastARYear === currentYear) this.$store.state.ARFilingYear = null
      else this.$store.state.ARFilingYear = +lastARYear + 1 + ''
    },
    getEntityInfo (corpNum) {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // when calling the api make sure this url is for most recent AR - stub specifies 2017 + add token in header
      corpNum = 'CP0001187'
      var url = corpNum
      axios.get(url).then(response => {
        this.entityInfoJson = response.data
        this.setEntityInfo()
      }).catch(error => console.log('getEntityInfo ERROR: ' + error + ' ' + axios.get))
    },
    setEntityInfo () {
      this.$store.state.entityName = this.entityInfoJson.business_info.legal_name
      this.$store.state.entityStatus = 'GOODSTANDING'
      this.$store.state.entityBusinessNo = '123456789'
      this.$store.state.entityIncNo = this.entityInfoJson.business_info.identifier
    },
    submit () {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // probably need to parametrize date=this.$store.state.currentDate + add token in header for api
      var url = this.payURL
      var paymentJson

      // other team doing credit card entering/payment confirmation? - don't know what to check for in result
      axios.get(url).then(response => {
        paymentJson = response.data
        console.log('payment response: ', paymentJson)
        if (paymentJson) this.$store.state.filedDate = this.$store.state.currentDate
      }).catch(error => console.log('payment ERROR: ' + error))
      this.$store.state.filedDate = this.$store.state.currentDate
    },
    resetARInfo () {
      this.$store.state.agmDate = null
      this.$store.state.filedDate = null
      this.$store.state.validated = false
      this.$store.state.noAGM = false
    },
    nextAR () {
      this.resetARInfo()
      this.getARInfo(this.$store.state.corpNum)
=======
    validated () {
      return this.$store.state.validated
    }
  },
  mounted () {
    this.setCorpNum()
  },
  methods: {
    setCorpNum () {
      // set corpnum, check for error
      this.$store.state.corpNum = sessionStorage.getItem('USERNAME')
      return true
    },
    setARInfo: function (corpNum) {
      // call legal-api for AGM with corpnum/userToken
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      console.log('Set AR Info')
      console.log(corpNum, ' ', token)
      var json = {
        filing: {
          header: {
            name: 'annual report',
            date: '2018-04-08'
          },
          business_info: {
            founding_date: '2001-08-05',
            identifier: 'CP6543210',
            legal_name: 'legal name'
          },
          annual_report: {
            annual_general_meeting_date: '2017-04-08',
            certified_by: 'full name',
            email: 'no_one@never.get'
          }
        }
      }
      // ##url: 'https://mock-lear-tools.pathfinder.gov.bc.ca/rest/legal-api/0.6/api/v1/businesses/CP6543210/filings/annual_report?year=2016'
      console.log('Run Axios get')
      var jjson
      //axios({
      //method: 'GET',
      //  url: 'https://mock-lear-test.pathfinder.gov.bc.ca/rest/Petstore+API/1.1/v2/pet/2?user_key=70f735676ec46351c6699c4bb767878a'
      //}).then(function(result) {
      //  jjson = result
      //}, error => console.log(error))
      // var url = 'https://mock-lear-test.pathfinder.gov.bc.ca/rest/Petstore+API/1.1/v2/pet/2?user_key=70f735676ec46351c6699c4bb767878a'
      //var url = 'https://mock-lear-tools.pathfinder.gov.bc.ca/rest/legal-api/0.64/api/v1/businesses/CP0001193/filings/annual_report?year=2017'
      var url = 'https://mock-lear-tools.pathfinder.gov.bc.ca/rest/Pay+API/0.6/pay-api/v1/fees/annual-report/CP?date=2019-04-15'
      axios.get(url).then(response => {
        console.log('Get JSON')
        jjson = response
        console.log(response)
      })
      console.log('done')
      console.log(jjson)
      console.log('other')
      var lastARYear = json.filing.header.date.substring(0, 4)
      var today = new Date()
      var currentYear = today.getFullYear() + ''
      if (lastARYear === currentYear) this.$store.state.ARFilingYear = null
      else this.$store.state.ARFilingYear = +lastARYear + 1 + ''
      return true
    },
    submit () {
      // hit pay stub
      // if success api call
      this.$store.state.ARFilingYear = null
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
    }
  },
  watch: {
    corpNum: function (val) {
<<<<<<< HEAD
      console.log('Home.vue corpNum watcher fired: ', val)
      if (val != null) {
        this.getARInfo(val)
        this.getEntityInfo(val)
=======
      console.log('Corp Num Watcher')
      // val = 1
      if (val != null) {
        this.setARInfo(val)
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
      }
    }
  }
}
</script>
