<template>
  <div class="home">

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

    <EntityInfo/>

    <AnnualReport ref="annualReport"/>

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
      regOffAddrJson: null,
      showLoading: false,
      loadingMsg: 'Redirecting to PayBC to Process Your Payment'
    }
  },
  computed: {
    corpNum () {
      return this.$store.state.corpNum
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
      this.getRegOffAddr(this.corpNum)
      this.$refs.annualReport.getDirectors()
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
      }).catch(error => {
        console.log('getARInfo ERROR: ' + error + ' ' + axios.get)
      })
    },
    getEntityInfo (corpNum) {
      var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      // todo:delete hardcoded corpnum when we stop pointing at mock
      corpNum = 'CP0001187'
      var url = corpNum
      axios.get(url).then(response => {
        this.entityInfoJson = response.data
        this.setEntityInfo()
      }).catch(error => {
        console.log('getEntityInfo ERROR: ' + error + ' ' + axios.get)
        // TODO - remove this stub data
        this.$store.state.entityName = 'Pathfinder Cooperative'
        this.$store.state.entityStatus = 'GOODSTANDING'
        this.$store.state.entityBusinessNo = '105023337BC0157'
        this.$store.state.entityIncNo = 'CP0015683'
      })
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
    }
  },
  watch: {
    corpNum: function (val) {
      console.log('Home.vue corpNum watcher fired: ', val)
      if (val != null) {
        this.getARInfo(val)
        this.getEntityInfo(val)
        this.getRegOffAddr(val)
        this.$refs.annualReport.getDirectors()
      }
    }
  }
}
</script>

<style scoped lang="stylus">
  @import "../assets/styles/theme.styl"

</style>
