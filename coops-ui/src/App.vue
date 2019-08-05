<template>
  <v-app class="app-container theme--light" id="app">
    <sbc-header v-bind:authURL="authAPIURL" />

    <div class="app-body">
      <main>
        <EntityInfo/>
        <router-view/>
      </main>
    </div>

    <sbc-footer />
  </v-app>
</template>

<script>
import EntityInfo from '@/components/EntityInfo.vue'
import { mapActions } from 'vuex'
import SbcHeader from 'sbc-common-components/src/components/SbcHeader.vue'
import SbcFooter from 'sbc-common-components/src/components/SbcFooter.vue'
import DateUtils from '@/DateUtils'

export default {
  name: 'App',

  mixins: [DateUtils],

  components: {
    SbcHeader,
    SbcFooter,
    EntityInfo
  },

  created () {
    // get Keycloak Token
    const token = sessionStorage.getItem('KEYCLOAK_TOKEN')
    if (!token) {
      console.error('App error - Keycloak Token is null')
      return
    }

    // decode Username
    const username = this.parseJwt(token).preferred_username
    if (!username) {
      console.error('App error - Username is null')
      return
    }

    // save tombstone data
    sessionStorage.setItem('USERNAME', username)
    this.setCorpNum(username.toUpperCase())
    this.saveCurrentDate()
  },

  methods: {
    ...mapActions(['setCorpNum', 'setCurrentDate']),

    parseJwt (token) {
      var base64Url = token.split('.')[1]
      var base64 = decodeURIComponent(atob(base64Url).split('').map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      return JSON.parse(base64)
    },

    saveCurrentDate () {
      // save current date as YYYY-MM-DD string
      // this logic works because Date() returns local time (plus offset which we ignore)
      // TODO: need some sort of event to update Current Date at midnight
      this.setCurrentDate(this.dateToUsableString(new Date()))
    }
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl"
  @import "./assets/styles/layout.styl"
  @import "./assets/styles/overrides.styl"
</style>
