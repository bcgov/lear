<template>
  <v-app class="app-container theme--light" id="app">

    <DashboardUnavailableDialog
      :dialog="dashboardUnavailableDialog"
      @exit="onClickExit"
      @retry="onClickRetry"
      attach="#app"
    />

    <AccountAuthorizationDialog
      :dialog="accountAuthorizationDialog"
      @exit="onClickExit"
      @retry="onClickRetry"
      attach="#app"
    />

    <!-- Initial Page Load Transition -->
    <transition name="fade">
      <div class="loading-container" v-show="showLoadingContainer">
        <div class="loading__content">
          <v-progress-circular color="primary" size="50" indeterminate />
          <div class="loading-msg">Loading Business Dashboard</div>
        </div>
      </div>
    </transition>

    <sbc-header ref="sbcHeader" />

    <div class="app-body">
      <main v-if="dataLoaded">
        <EntityInfo />
        <router-view />
      </main>
    </div>

    <sbc-footer />

  </v-app>
</template>

<script>
// Libraries
import { mapActions, mapState } from 'vuex'
import axios from '@/axios-auth'

// Components
import SbcHeader from 'sbc-common-components/src/components/SbcHeader.vue'
import SbcFooter from 'sbc-common-components/src/components/SbcFooter.vue'
import EntityInfo from '@/components/EntityInfo.vue'

// Dialogs
import { DashboardUnavailableDialog, AccountAuthorizationDialog } from '@/components/dialogs'

// Mixins
import { DateMixin, CommonMixin, DirectorMixin } from '@/mixins'

// Folder containing the array of configuration objects
import { configJson } from '@/resources'

export default {
  name: 'App',

  mixins: [DateMixin, CommonMixin, DirectorMixin],

  data () {
    return {
      dataLoaded: false,
      dashboardUnavailableDialog: false,
      accountAuthorizationDialog: false
    }
  },

  components: {
    DashboardUnavailableDialog,
    AccountAuthorizationDialog,
    SbcHeader,
    SbcFooter,
    EntityInfo
  },

  computed: {
    ...mapState(['triggerDashboardReload']),

    authAPIURL () {
      return sessionStorage.getItem('AUTH_API_URL')
    },

    showLoadingContainer () {
      return !this.dataLoaded && !this.dashboardUnavailableDialog && !this.accountAuthorizationDialog
    }
  },

  created () {
    // fetch all data
    this.fetchData()
  },

  methods: {
    ...mapActions(['setKeycloakRoles', 'setAuthRoles', 'setBusinessEmail', 'setBusinessPhone',
      'setBusinessPhoneExtension', 'setCurrentDate', 'setEntityName', 'setEntityType', 'setEntityStatus',
      'setEntityBusinessNo', 'setEntityIncNo', 'setLastPreLoadFilingDate', 'setEntityFoundingDate', 'setLastAgmDate',
      'setNextARDate', 'setTasks', 'setFilings', 'setRegisteredAddress', 'setRecordsAddress', 'setDirectors',
      'setTriggerDashboardReload', 'setLastAnnualReportDate', 'setConfigObject']),

    fetchData () {
      this.dataLoaded = false
      let businessId

      try {
        // get initial data
        const jwt = this.getJWT()
        const keycloakRoles = this.getKeycloakRoles(jwt)
        this.setKeycloakRoles(keycloakRoles)
        businessId = this.getBusinessId()
        this.updateCurrentDate()
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error(error)
        this.dashboardUnavailableDialog = true
        return // do not execute remaining code
      }

      // check if current user is authorized
      this.getAuthorizations(businessId).then(data => {
        this.storeAuthRoles(data) // throws if no role

        // good so far ... fetch the rest of the data
        Promise.all([
          this.getBusinessInfo(businessId),
          axios.get(businessId),
          axios.get(businessId + '/tasks'),
          axios.get(businessId + '/filings'),
          axios.get(businessId + '/addresses'),
          axios.get(businessId + '/directors')
        ]).then(data => {
          if (!data || data.length !== 6) throw new Error('Incomplete data')
          this.storeBusinessInfo(data[0])
          this.storeEntityInfo(data[1])
          this.storeTasks(data[2])
          this.storeFilings(data[3])
          this.storeAddresses(data[4])
          this.storeDirectors(data[5])
          this.dataLoaded = true
        }).catch(error => {
          // eslint-disable-next-line no-console
          console.error(error)
          this.dashboardUnavailableDialog = true
        })
      }).catch(error => {
        // eslint-disable-next-line no-console
        console.error(error)
        this.accountAuthorizationDialog = true
      })
    },

    getJWT () {
      const token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      if (token) {
        return this.parseJwt(token)
      }
      throw new Error('Error getting Keycloak token')
    },

    parseJwt (token) {
      try {
        const base64Url = token.split('.')[1]
        const base64 = decodeURIComponent(window.atob(base64Url).split('').map(function (c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
        }).join(''))
        return JSON.parse(base64)
      } catch (error) {
        throw new Error('Error parsing JWT - ' + error)
      }
    },

    getKeycloakRoles (jwt) {
      const keycloakRoles = jwt.roles
      if (keycloakRoles && keycloakRoles.length > 0) {
        return keycloakRoles
      }
      throw new Error('Error getting Keycloak roles')
    },

    getBusinessId () {
      const businessId = sessionStorage.getItem('BUSINESS_IDENTIFIER')
      if (businessId) {
        return businessId
      }
      throw new Error('Error getting business identifier')
    },

    updateCurrentDate () {
      const now = new Date()
      const date = this.dateToUsableString(now)
      this.setCurrentDate(date)
      // set timeout to run this again at midnight
      const hoursToMidnight = 23 - now.getHours()
      const minutesToMidnight = 59 - now.getMinutes()
      const secondsToMidnight = 59 - now.getSeconds()
      const timeout = ((((hoursToMidnight * 60) + minutesToMidnight) * 60) + secondsToMidnight) * 1000
      setTimeout(this.updateCurrentDate, timeout)
    },

    getAuthorizations (businessId) {
      const url = businessId + '/authorizations'
      const config = {
        baseURL: this.authAPIURL + 'entities/'
      }
      return axios.get(url, config)
    },

    getBusinessInfo (businessId) {
      const url = businessId
      const config = {
        baseURL: this.authAPIURL + 'entities/'
      }
      return axios.get(url, config)
    },

    storeAuthRoles (response) {
      // NB: roles array may contain 'view', 'edit' or nothing
      const authRoles = response && response.data && response.data.roles
      if (authRoles && authRoles.length > 0) {
        this.setAuthRoles(authRoles)
      } else {
        throw new Error('Invalid auth roles')
      }
    },

    storeBusinessInfo (response) {
      const contacts = response && response.data && response.data.contacts
      // ensure we received the right looking object
      // but allow empty contacts array
      if (contacts) {
        // at this time there is at most 1 contact
        const contact = contacts.length > 0 && contacts[0]
        if (contact) {
          this.setBusinessEmail(contact.email)
          this.setBusinessPhone(contact.phone)
          this.setBusinessPhoneExtension(contact.phoneExtension)
        }
      } else {
        throw new Error('Invalid business contact info')
      }
    },

    storeEntityInfo (response) {
      if (response && response.data && response.data.business) {
        this.setEntityName(response.data.business.legalName)
        this.setEntityType(response.data.business.legalType)
        this.setNextARDate(response.data.business.nextAnnualReport)
        this.setEntityStatus(response.data.business.status)
        this.setEntityBusinessNo(response.data.business.taxId)
        this.setEntityIncNo(response.data.business.identifier)
        this.setLastPreLoadFilingDate(response.data.business.lastLedgerTimestamp
          ? response.data.business.lastLedgerTimestamp.split('T')[0] : null)
        this.setEntityFoundingDate(response.data.business.foundingDate) // datetime
        this.setLastAnnualReportDate(response.data.business.lastAnnualReport)
        this.storeConfigObject(response.data.business.legalType)
        const date = response.data.business.lastAnnualGeneralMeetingDate
        if (
          date &&
          date.length === 10 &&
          date.indexOf('-') === 4 &&
          date.indexOf('-', 5) === 7 &&
          date.indexOf('-', 8) === -1
        ) {
          this.setLastAgmDate(date)
        } else {
          this.setLastAgmDate(null)
        }
      } else {
        throw new Error('Invalid entity info')
      }
    },

    storeTasks (response) {
      if (response && response.data && response.data.tasks) {
        this.setTasks(response.data.tasks)
      } else {
        throw new Error('Invalid tasks')
      }
    },

    storeFilings (response) {
      if (response && response.data && response.data.filings) {
        this.setFilings(response.data.filings)
      } else {
        throw new Error('Invalid filings')
      }
    },

    storeAddresses (response) {
      if (response && response.data) {
        if (response.data.registeredOffice) {
          this.setRegisteredAddress(this.omitProps(response.data.registeredOffice,
            ['deliveryAddress', 'mailingAddress'],
            ['addressType']))
        }
        if (response.data.recordsOffice) {
          this.setRecordsAddress(this.omitProps(response.data.recordsOffice,
            ['deliveryAddress', 'mailingAddress'],
            ['addressType']))
        }
      } else {
        throw new Error('invalid office addresses')
      }
    },

    storeDirectors (response) {
      if (response && response.data && response.data.directors) {
        const directorsList = response.data.directors
        const directors = directorsList.sort(this.fieldSorter(['lastName', 'firstName', 'middleName']))
        for (var i = 0; i < directors.length; i++) {
          directors[i].id = i + 1
          directors[i].isNew = false
          directors[i].isDirectorActive = true
        }
        this.setDirectors(directors)
      } else {
        throw new Error('Invalid directors')
      }
    },

    storeConfigObject (entityType) {
      const configObject = configJson.find(x => x.typeEnum === entityType)
      this.setConfigObject(configObject)
    },

    onClickExit () {
      const businessesUrl = sessionStorage.getItem('BUSINESSES_URL') || ''
      // assume Businesses URL is always reachable
      businessesUrl && window.location.assign(businessesUrl)
    },

    onClickRetry () {
      this.dashboardUnavailableDialog = false
      this.accountAuthorizationDialog = false
      this.fetchData()
    }
  },

  watch: {
    '$route' () {
      // if we (re)route to the dashboard then re-fetch all data
      // (does not fire on initial dashboard load)
      if (this.$route.name === 'dashboard') {
        this.fetchData()
      }
    },

    triggerDashboardReload (val) {
      if (val) {
        this.fetchData()
        this.setTriggerDashboardReload(false)
      }
    }
  }
}
</script>

<style lang="scss">
// @import '@/assets/styles/theme.scss';
</style>
