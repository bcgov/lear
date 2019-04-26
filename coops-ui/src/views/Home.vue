<template>
  <div class="home">
    <v-app>
      <EntityInfo/>
      <AnnualReport/>
      <v-container>
        <v-btn v-if="filedDate == null" color="blue" :disabled="!validated" @click="submit">Pay</v-btn>
        <v-btn v-else color="blue" :disabled="currentYear == ARFilingYear" @click="nextAR">Next</v-btn>
      </v-container>
    </v-app>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import axios from 'axios'
import EntityInfo from '@/components/EntityInfo.vue'
import AnnualReport from '@/components/AnnualReport.vue'
import Keycloak from '../assets/js/keycloak.js'

export default {
  name: 'Home.vue',
  components: {
    EntityInfo,
    AnnualReport
  },
  data () {
    return {
      lastARJson: null
    }
  },
  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
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

    this.setCorpNum()
    if (this.ARFilingYear == null) this.getARInfo(this.corpNum)
  },
  methods: {
    setCorpNum () {
      // set corpnum, check for error
      this.$store.state.corpNum = sessionStorage.getItem('USERNAME')
      if (this.$store.state.corpNum == null) {
        console.error('No USERNAME set in sessionStorage - cannot get corpNum')
      } else {
        this.$store.state.corpNum = this.$store.state.corpNum.toUpperCase()
      }
    },
    getARInfo (corpNum) {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // when calling the api make sure this url is for most recent AR - stub specifies 2017 + add token in header
      var url = '/api/v1/businesses/' + corpNum + '/filings/annual_report?year=2017'

      axios.get(url).then(response => {
        this.lastARJson = response.data
        this.setARInfo()
      }).catch(error => console.log('ERROR: ' + error))
    },
    setARInfo () {
      var lastARYear = this.lastARJson.filing.annual_report.annual_general_meeting_date.substring(0, 4)
      var currentYear = (new Date()).getFullYear() + ''

      if (lastARYear === currentYear) this.$store.state.ARFilingYear = null
      else this.$store.state.ARFilingYear = +lastARYear + 1 + ''
    },
    submit () {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // probably need to parametrize date=this.$store.state.currentDate + add token in header for api
      var url = '/v1/fees/annual-report/CP?date=2019-04-15'
      var paymentJson

      // other team doing credit card entering/payment confirmation? - don't know what to check in resulting json for
      // success/failure
      axios.get(url).then(response => {
        paymentJson = response.data
        console.log('payment response: ', paymentJson)
        if (paymentJson) this.$store.state.filedDate = this.$store.state.currentDate
      }).catch(error => console.log('ERROR: ' + error))
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
    }
  },
  watch: {
    corpNum: function (val) {
      console.log('Home.vue corpNum watcher fired: ', val)
      if (val != null) {
        this.getARInfo(val)
      }
    }
  }
}
</script>
