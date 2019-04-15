<template>
  <div class="home">
    <v-app>
      <EntityInfo/>
      <AnnualReport/>
      <v-container>
        <v-btn color="blue" :disabled="!validated" @click="submit">Pay</v-btn>
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
  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
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
    setARInfo (corpNum) {
      // call legal-api for AGM with corpnum/userToken
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
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
      // hit pay stub
      // if success api call
      this.$store.state.ARFilingYear = null
    }
  },
  watch: {
    corpNum: function (val) {
      if (val != null) {
        this.setARInfo(val)
      }
    }
  }
}
</script>
