<template>
  <header class="app-header" fixed app>
    <div class="container">
      <router-link to="/" class="navbar-brand">
        <img class="brand-img" src="@/assets/images/gov3_bc_logo.png"
          alt="Province of British Columbia Logo"
          title="Province of British Columbia"/>
      </router-link>
      <span class="bcros">BC Registries & Online Services</span>
      <!-- <span class="bcros" v-show="this.$route.name != 'PayBC'">BC Registries & Online Services</span> -->
      <!-- <span class="paybc-logo" v-show="this.$route.name === 'PayBC'">Pay<strong>BC</strong></span> -->
      <div class="app-header__actions">
        <v-btn outline color="#ffffff"><span>Sign out</span></v-btn>
      </div>
    </div>
  </header>
</template>
<script>

export default {
  name: 'StdHeader.vue'
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .app-header
    position fixed
    width 100%
    color #fff
    border-bottom 3px solid $BCgovGold5
    background-color $BCgovBlue5

    .container
      display flex
      align-items center
      padding-top 0
      padding-bottom 0

  .app-header__actions
    margin-left auto

    .v-btn
      margin-right 0

  .brand-img
    margin-top 0.3rem
    margin-right 1.5rem
    margin-left -0.1rem

  .bcros
    margin-top 0.2rem
    font-size 1.125rem
    font-weight 300

  .paybc-logo {
    margin-top 0.45rem
    display: inline-block
    font-size 2.25rem
    font-weight 600
    vertical-align top

    strong {
      color $BCgovGold5
      font-weight 600
    }
  }

</style>
