<template>
  <div id="app">
    <std-header></std-header>
    <router-view/>
  </div>
</template>
<script>
import StdHeader from '@/components/StdHeader.vue'
export default {
  name: 'App',
  components: {
    StdHeader
  },
  mounted () {
    if (sessionStorage.getItem('KEYCLOAK_TOKEN')) {
      sessionStorage.setItem('USERNAME', this.parseJwt(sessionStorage.getItem('KEYCLOAK_TOKEN')).preferred_username)
      this.setCorpNum()
    }
  },
  methods: {
    parseJwt (token) {
      var base64Url = token.split('.')[1]
      var base64 = decodeURIComponent(atob(base64Url).split('').map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))

      return JSON.parse(base64)
    },
    setCorpNum () {
      // set corpnum, check for error'
      this.$store.state.corpNum = sessionStorage.getItem('USERNAME')
      if (this.$store.state.corpNum == null) {
        console.error('No USERNAME - cannot get corpNum')
      } else {
        this.$store.state.corpNum = this.$store.state.corpNum.toUpperCase()
      }
    }
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl";
  @import "./assets/styles/layout.styl";
  .view-container, .container
    width 100%
</style>
