<template>
  <v-app class="app-container theme--light" id="app">

    <!-- Initial Page Load Transition -->
    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
        <div class="loading-msg">Loading Your Dashboard</div>
      </div>
    </div>

    <v-dialog v-model="dashboardUnavailableDialog" width="45rem" persistent>
      <v-card>
        <v-card-title>Dashboard Unavailable</v-card-title>
        <v-card-text>
          <p class="genErr">We are currently unable to access your dashboard. You can continue to
            try to access your dashboard, or you can exit now and try to access your dashboard at
            another time.</p>
          <p class="genErr">If this error persists, please contact us.</p>
          <p class="genErr">
            <v-icon small>phone</v-icon>
            <a href="tel:+1-250-952-0568" class="error-dialog-padding">250 952-0568</a>
          </p>
          <p class="genErr">
            <v-icon small>email</v-icon>
            <a href="mailto:SBC_ITOperationsSupport@gov.bc.ca" class="error-dialog-padding"
              >SBC_ITOperationsSupport@gov.bc.ca</a>
          </p>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-btn color="primary" flat @click="onClickExit">Exit</v-btn>
          <v-spacer></v-spacer>
          <v-btn color="primary" flat @click="onClickRetry">Retry</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <sbc-header ref="sbcHeader" v-bind:authURL="authAPIURL" />

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
import { mapActions } from 'vuex'
import DateUtils from '@/DateUtils'
import axios from '@/axios-auth'
import SbcHeader from 'sbc-common-components/src/components/SbcHeader.vue'
import SbcFooter from 'sbc-common-components/src/components/SbcFooter.vue'
import EntityInfo from '@/components/EntityInfo.vue'

export default {
  name: 'App',

  mixins: [DateUtils],

  data () {
    return {
      dashboardUnavailableDialog: false,
      dataLoaded: false
    }
  },

  components: {
    SbcHeader,
    SbcFooter,
    EntityInfo
  },

  computed: {
    authAPIURL () {
      return sessionStorage.getItem('AUTH_API_URL')
    }
  },

  created () {
    // fetch all data
    this.fetchData()
  },

  methods: {
    ...mapActions(['setCorpNum', 'setCurrentDate', 'setEntityName', 'setEntityStatus', 'setEntityBusinessNo',
      'setEntityIncNo', 'setLastPreLoadFilingDate', 'setEntityFoundingDate', 'setLastAgmDate', 'setTasks',
      'setFilings', 'setMailingAddress', 'setDeliveryAddress', 'setDirectors']),

    fetchData () {
      let corpNum = null

      // first try synchronous operations
      try {
        // get Keycloak Token
        const token = sessionStorage.getItem('KEYCLOAK_TOKEN')
        if (!token) {
          throw new Error('Keycloak Token is null')
        }

        // decode Username
        const username = this.parseJwt(token).preferred_username
        if (!username) {
          throw new Error('Username is null')
        }

        // save tombstone data
        sessionStorage.setItem('USERNAME', username)
        corpNum = username.toUpperCase()
        this.setCorpNum(corpNum)
        this.setCurrentDate(this.dateToUsableString(new Date()))
      } catch (error) {
        console.error(error)
        this.dashboardUnavailableDialog = true
        return // do not execute remaining code
      }

      // now execute async operations
      Promise.all([
        axios.get(corpNum),
        axios.get(corpNum + '/tasks'),
        axios.get(corpNum + '/filings'),
        axios.get(corpNum + '/addresses'),
        axios.get(corpNum + '/directors')
      ]).then(data => {
        if (!data || data.length !== 5) throw new Error('incomplete data')
        this.storeEntityInfo(data[0])
        this.storeTasks(data[1])
        this.storeFilings(data[2])
        this.storeAddresses(data[3])
        this.storeDirectors(data[4])
        this.dataLoaded = true
      }).catch(error => {
        console.error(error)
        this.dashboardUnavailableDialog = true
      })
    },

    parseJwt (token) {
      var base64Url = token.split('.')[1]
      var base64 = decodeURIComponent(atob(base64Url).split('').map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      return JSON.parse(base64)
    },

    storeEntityInfo (response) {
      if (response && response.data && response.data.business) {
        this.setEntityName(response.data.business.legalName)
        this.setEntityStatus(response.data.business.status)
        this.setEntityBusinessNo(response.data.business.taxId)
        this.setEntityIncNo(response.data.business.identifier)
        this.setLastPreLoadFilingDate(response.data.business.lastLedgerTimestamp
          ? response.data.business.lastLedgerTimestamp.split('T')[0] : null)
        this.setEntityFoundingDate(response.data.business.foundingDate
          ? response.data.business.foundingDate.split('T')[0] : null)
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
        throw new Error('invalid entity info')
      }
    },

    storeTasks (response) {
      if (response && response.data && response.data.tasks) {
        this.setTasks(response.data.tasks)
      } else {
        throw new Error('invalid tasks')
      }
    },

    storeFilings (response) {
      if (response && response.data && response.data.filings) {
        // sort by date descending (ie, latest to earliest)
        const filings = response.data.filings.sort(
          (a, b) => (b.filing.header.date - a.filing.header.date)
        )
        this.setFilings(filings)
      } else {
        throw new Error('invalid filings')
      }
    },

    storeAddresses (response) {
      if (response && response.data && response.data.mailingAddress) {
        this.setMailingAddress(response.data.mailingAddress)
      } else {
        throw new Error('invalid mailing address')
      }
      if (response && response.data && response.data.deliveryAddress) {
        this.setDeliveryAddress(response.data.deliveryAddress)
      } else {
        throw new Error('invalid delivery address')
      }
    },

    storeDirectors (response) {
      if (response && response.data && response.data.directors) {
        const directors = response.data.directors
        for (var i = 0; i < directors.length; i++) {
          directors[i].id = i + 1
          directors[i].isNew = false
          directors[i].isDirectorActive = true
        }
        this.setDirectors(directors)
      } else {
        throw new Error('invalid directors')
      }
    },

    onClickExit () {
      this.$refs.sbcHeader.logout()
    },

    onClickRetry () {
      this.dashboardUnavailableDialog = false
      this.$nextTick(() => this.fetchData())
    }
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl"
  @import "./assets/styles/layout.styl"
  @import "./assets/styles/overrides.styl"
</style>
