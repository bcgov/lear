<template>
  <v-app class="app-container theme--light" id="app">
    <std-header></std-header>

    <div class="app-body">
      <main>
        <EntityInfo/>

        <router-view/>
      </main>
    </div>
  </v-app>
</template>

<script>
import axios from '@/axios-auth'
import StdHeader from '@/components/StdHeader.vue'
import EntityInfo from '@/components/EntityInfo.vue'

export default {
  name: 'App',

  components: {
    StdHeader,
    EntityInfo
  },

  data () {
    return {
      username: null
    }
  },

  computed: {
    corpNum () {
      return this.$store.state.corpNum
    }
  },

  mounted () {
    // get current date
    // this logic works because Date() returns local time (plus offset which we ignore)
    // TODO: need some sort of event to update Current Date midnight
    const today = new Date()
    const year = today.getFullYear().toString()
    const month = (today.getMonth() + 1).toString().padStart(2, '0')
    const date = today.getDate().toString().padStart(2, '0')
    this.$store.state.currentDate = `${year}-${month}-${date}`

    // get tombstone data
    this.getUsername()
    this.getCorpNum()
  },

  methods: {
    getUsername () {
      const token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      if (!token) {
        console.log('getUsername() error - Token is null')
      } else {
        this.username = this.parseJwt(token).preferred_username
      }
    },
    parseJwt (token) {
      var base64Url = token.split('.')[1]
      var base64 = decodeURIComponent(atob(base64Url).split('').map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      return JSON.parse(base64)
    },
    getCorpNum () {
      if (!this.username) {
        console.log('getCorpNum() error - Username is null')
      } else {
        // right now, Username is Corp Num
        this.$store.state.corpNum = this.username.toUpperCase()
        // TODO - overwrite Corp Num as follows for local testing
        // this.$store.state.corpNum = 'CP0002098'
      }
    },
    getEntityInfo () {
      if (this.corpNum) {
        const url = this.corpNum
        axios.get(url).then(response => {
          if (response && response.data && response.data.business) {
            this.$store.state.entityName = response.data.business.legalName
            this.$store.state.entityStatus = response.data.business.status
            this.$store.state.entityBusinessNo = response.data.business.taxId
            this.$store.state.entityIncNo = response.data.business.identifier
            this.$store.state.lastAgmDate =
              this.isValidateDateFormat(response.data.business.lastAnnualGeneralMeetingDate)
                ? response.data.business.lastAnnualGeneralMeetingDate
                : null
          } else {
            console.log('getEntityInfo() error - invalid response data')
          }
        }).catch(error => console.error('getEntityInfo() error =', error))
      }
    },
    isValidateDateFormat (date) {
      // validate ISO date format (YYYY-MM-DD)
      return (date &&
        date.length === 10 &&
        date.indexOf('-') === 4 &&
        date.indexOf('-', 5) === 7 &&
        date.indexOf('-', 8) === -1)
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num changes, get new entity info
      this.getEntityInfo()
    }
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl";
  @import "./assets/styles/layout.styl";
  @import "./assets/styles/overrides.styl";
</style>
