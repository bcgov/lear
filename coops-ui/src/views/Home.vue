<template>
  <div class="home">
    <v-app>
      <EntityInfo/>
      <AnnualReport/>
      <v-container>
        <v-btn v-if="filedDate == null" id='ar-pay-btn' color="blue" :disabled="!validated" @click="submit">Pay</v-btn>
        <v-btn v-else color="blue" id='ar-next-btn' :disabled="currentYear == ARFilingYear" @click="nextAR">Next</v-btn>
      </v-container>
    </v-app>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import axios from '@/axios-auth.ts'
import EntityInfo from '@/components/EntityInfo.vue'
import AnnualReport from '@/components/AnnualReport.vue'

export default {
  name: 'Home.vue',
  components: {
    EntityInfo,
    AnnualReport
  },
  data () {
    return {
      lastARJson: null,
      entityInfoJson: null
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
    }
  },
  watch: {
    corpNum: function (val) {
      console.log('Home.vue corpNum watcher fired: ', val)
      if (val != null) {
        this.getARInfo(val)
        this.getEntityInfo(val)
      }
    }
  }
}
</script>
