<template>
  <v-app class="app-container theme--light" id="app">
    <std-header></std-header>
    <div class="app-body">
      <main>
         <EntityInfo />
        <router-view/>
      </main>
    </div>
  </v-app>
</template>

<script>
import StdHeader from '@/components/StdHeader.vue'
import EntityInfo from '@/components/EntityInfo.vue'
import { mapActions } from 'vuex'

export default {
  name: 'App',
  components: {
    StdHeader,
    EntityInfo
  },
  created () {
    if (sessionStorage.getItem('KEYCLOAK_TOKEN')) {
      sessionStorage.setItem('USERNAME', this.parseJwt(sessionStorage.getItem('KEYCLOAK_TOKEN')).preferred_username)
      this.saveCorpNum()
      this.saveCurrentDate()
    }
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
    saveCorpNum () {
      if (sessionStorage.getItem('USERNAME') == null) {
        console.error('No USERNAME - cannot get corpNum')
      } else {
        this.setCorpNum(sessionStorage.getItem('USERNAME').toString().toUpperCase())
      }
    },
    saveCurrentDate () {
      const today = new Date()
      const year = today.getFullYear().toString()
      const month = (today.getMonth() + 1).toString().padStart(2, '0')
      const date = today.getDate().toString().padStart(2, '0')
      this.setCurrentDate(`${year}-${month}-${date}`)
    }
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl";
  @import "./assets/styles/layout.styl";
  @import "./assets/styles/overrides.styl";
</style>
