<template>
  <div class="home">
    <v-app>
      <v-container id="entity-info-container" class="view-container">
        <EntityInfo/>
      </v-container>
      <v-container id="annual-report-container" class="view-container">
        <AnnualReport/>
      </v-container>
      <v-container id="submit-container" class="view-container">
        <v-btn v-if="filedDate == null" id='ar-pay-btn' color="blue" :disabled="!validated" @click="submit">Pay</v-btn>
        <v-btn v-else color="blue" id='ar-next-btn' :disabled="currentYear == ARFilingYear" @click="nextAR">Next</v-btn>
      </v-container>
    </v-app>
  </div>
</template>

<script lang="ts">
import axios from '../axios-auth'
import EntityInfo from '@/components/EntityInfo.vue'
import AnnualReport from '@/components/AnnualReport.vue'
export default {
  name: 'Home',
  components: {
    EntityInfo,
    AnnualReport
  },
  data () {
    return {
      lastARJson: null,
      entityInfoJson: null,
      regOffAddrJson: null
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
    },
    regOffAddrChange () {
      return this.$store.state.regOffAddrChange
    }
  },
  mounted () {
    var today = new Date()
    this.$store.state.currentDate = today.getFullYear() + '-' + ('0' + (+today.getMonth() + 1)).slice(-2) + '-' +
      ('0' + today.getDate()).slice(-2)

    if (this.ARFilingYear == null && this.corpNum != null) {
      this.getARInfo(this.corpNum)
      this.getEntityInfo(this.corpNum)
      this.getRegOffAddr(this.corpNum)
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
    getEntityInfo (corpNum) {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // todo:delete hardcoded corpnum when we stop pointing at mock
      corpNum = 'CP0001187'
      var url = corpNum
      axios.get(url).then(response => {
        this.entityInfoJson = response.data
        this.setEntityInfo()
      }).catch(error => console.log('getEntityInfo ERROR: ' + error + ' ' + axios.get))
    },
    getRegOffAddr (corpNum) {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // todo:change endpoint to real one
      var url = corpNum + '/filings/registered_office'
      // todo:delete hardcoded json and make axios call
      // axios.get(url).then(response => {
      //   this.regOffAddrJson = response.data
      //   this.setRegOffAddr()
      // }).catch(error => console.log('getRegOffAddr ERROR: ' + error + ' ' + axios.get))
      this.regOffAddrJson = {
        header: {},
        business_info: {},
        filing: {
          certifiedBy: 'tester',
          email: 'tester@testing.com',
          deliveryAddress: {
            streetAddress: '1234 Main Street',
            streetAddressAdditional: '',
            addressCity: 'Victoria',
            addressRegion: 'BC',
            addressCountry: 'Canada',
            postalCode: 'V9A 2G8',
            deliveryInstructions: ''
          },
          mailingAddress: {
            streetAddress: '1234 Main Street',
            streetAddressAdditional: '',
            addressCity: 'Victoria',
            addressRegion: 'BC',
            addressCountry: 'Canada',
            postalCode: 'V9A 2G8',
            deliveryInstructions: ''
          }
        }
      }
      this.setRegOffAddr()
    },
    setARInfo () {
      var lastARYear = this.lastARJson.filing.annual_report.annual_general_meeting_date.substring(0, 4)
      var currentYear = (new Date()).getFullYear() + ''
      if (lastARYear === currentYear) this.$store.state.ARFilingYear = null
      else this.$store.state.ARFilingYear = +lastARYear + 1 + ''
    },
    setEntityInfo () {
      // todo:take out hardcoded values after api returns proper values
      this.$store.state.entityName = this.entityInfoJson.business_info.legal_name
      this.$store.state.entityStatus = 'GOODSTANDING'
      this.$store.state.entityBusinessNo = '123456789'
      this.$store.state.entityIncNo = this.entityInfoJson.business_info.identifier
    },
    setRegOffAddr () {
      this.$store.state.DeliveryAddressStreet = this.regOffAddrJson.filing.deliveryAddress.streetAddress
      this.$store.state.DeliveryAddressStreetAdditional =
        this.regOffAddrJson.filing.deliveryAddress.streetAddressAdditional
      this.$store.state.DeliveryAddressCity = this.regOffAddrJson.filing.deliveryAddress.addressCity
      this.$store.state.DeliveryAddressRegion = this.regOffAddrJson.filing.deliveryAddress.addressRegion
      this.$store.state.DeliveryAddressPostalCode = this.regOffAddrJson.filing.deliveryAddress.postalCode
      this.$store.state.DeliveryAddressCountry = this.regOffAddrJson.filing.deliveryAddress.addressCountry
      this.$store.state.DeliveryAddressInstructions = this.regOffAddrJson.filing.deliveryAddress.deliveryInstructions

      this.$store.state.MailingAddressStreet = this.regOffAddrJson.filing.mailingAddress.streetAddress
      this.$store.state.MailingAddressStreetAdditional =
        this.regOffAddrJson.filing.mailingAddress.streetAddressAdditional
      this.$store.state.MailingAddressCity = this.regOffAddrJson.filing.mailingAddress.addressCity
      this.$store.state.MailingAddressRegion = this.regOffAddrJson.filing.mailingAddress.addressRegion
      this.$store.state.MailingAddressPostalCode = this.regOffAddrJson.filing.mailingAddress.postalCode
      this.$store.state.MailingAddressCountry = this.regOffAddrJson.filing.mailingAddress.addressCountry
      this.$store.state.MailingAddressInstructions = this.regOffAddrJson.filing.mailingAddress.deliveryInstructions
    },
    submit () {
      // todo: redirect to payment - will need to save state of page
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
      this.$store.state.regOffAddrChange = false
      this.setRegOffAddrNull()
      this.$router.go()
    },
    nextAR () {
      this.resetARInfo()
      this.getARInfo(this.corpNum)
    },
    setRegOffAddrNull () {
      this.$store.state.DeliveryAddressStreet = null
      this.$store.state.DeliveryAddressStreetAdditional = null
      this.$store.state.DeliveryAddressCity = null
      this.$store.state.DeliveryAddressRegion = null
      this.$store.state.DeliveryAddressPostalCode = null
      this.$store.state.DeliveryAddressCountry = null
      this.$store.state.DeliveryAddressInstructions = null
      this.$store.state.MailingAddressStreet = null
      this.$store.state.MailingAddressStreetAdditional = null
      this.$store.state.MailingAddressCity = null
      this.$store.state.MailingAddressRegion = null
      this.$store.state.MailingAddressPostalCode = null
      this.$store.state.MailingAddressCountry = null
      this.$store.state.MailingAddressInstructions = null
    }
  },
  watch: {
    corpNum: function (val) {
      console.log('Home.vue corpNum watcher fired: ', val)
      if (val != null) {
        this.getARInfo(val)
        this.getEntityInfo(val)
        this.getRegOffAddr(val)
      }
    },
    regOffAddrChange: function (val) {
      console.log('Home.vue regOffAddrChange watcher fired: ', val)
      // if (val && this.$store.state.agmDate == null) this.$store.state.validated = true
    }
  }
}
</script>

<style lang="stylus">
@import "../assets/styles/theme.styl"

  #annual-report-container, #entity-info-container, #submit-container
    margin 0
    padding 1rem
  #entity-info-container
    margin-top .01rem
    max-width none
    max-height 6rem
    background-color white
  #submit-container
    margin-left 1rem
</style>
