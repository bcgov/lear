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
    this.getUsername()
    this.getCorpNum()
    this.getEntityInfo()
  },

  methods: {
    getUsername () {
      const token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      if (!token) {
        console.error('getUsername() error - Token is null')
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
        console.error('getCorpNum() error - Username is null')
      } else {
        // TODO - reinstate this when token is fixed
        // this.$store.state.corpNum = this.username.toUpperCase()
        this.$store.state.corpNum = 'CP1234567'
      }
    },
    getEntityInfo () {
      if (!this.corpNum) {
        console.error('getEntityInfo() error - Corp Num is null')
      } else {
        axios.get(this.corpNum).then(response => {
          const entityInfoJson = response.data
          // TODO - remove fallback data when API returns proper values
          this.$store.state.entityName = entityInfoJson.business.legalName
          this.$store.state.entityStatus = entityInfoJson.business.status
          this.$store.state.entityBusinessNo = entityInfoJson.business.taxId
          this.$store.state.entityIncNo = entityInfoJson.business.identifier
        }).catch(error => {
          console.log('getEntityInfo ERROR:', error)
        })
      }
    }
  },

  watch: {
    // TODO - remove this if Corp Num never changes
    // corpNum (val) {
    //   console.log('corpNum =', val)
    //   if (val) {
    //     this.getEntityInfo()
    //   }
    // }
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl";
  @import "./assets/styles/layout.styl";
  @import "./assets/styles/overrides.styl";
</style>
