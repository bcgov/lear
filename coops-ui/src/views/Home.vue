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
      json: {
        filing: {
          header: {
            name: 'annual report',
            date: '2017-04-08'
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
    this.setCorpNum()
    if (this.ARFilingYear == null) this.setARInfo(this.corpNum, this.json)
  },
  methods: {
    setCorpNum () {
      // set corpnum, check for error
      this.$store.state.corpNum = sessionStorage.getItem('USERNAME')
      return true
    },
    setARInfo (corpNum, json) {
      // call legal-api for AGM with corpnum/userToken
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      console.log(corpNum, ' ', token)
      // axios({
      //   method: 'GET',
      //   url: 'https://mock-lear-tools.pathfinder.gov.bc.ca/rest/legal-api/0.6/api/v1/businesses/CP6543210/filings/annual_report?year=2016',
      //   headers: {}
      // }).then(result => { json = result }, error => console.error(error))
      console.log(json)
      var lastARYear = json.filing.header.date.substring(0, 4)
      var today = new Date()
      var currentYear = today.getFullYear() + ''
      if (lastARYear === currentYear) this.$store.state.ARFilingYear = null
      else this.$store.state.ARFilingYear = +lastARYear + 1 + ''
      return true
    },
    submit () {
      this.$store.state.filedDate = this.$store.state.currentDate
    },
    nextAR () {
      this.json.filing.header.date = '2018-04-08'
      this.$store.state.agmDate = null
      this.$store.state.filedDate = null
      this.$store.state.validated = false
      this.$store.state.noAGM = false
      this.setARInfo(this.corpNum, this.json)
    }
  },
  watch: {
    corpNum: function (val) {
      if (val != null) {
        this.setARInfo(val, this.json)
      }
    }
  }
}
</script>
