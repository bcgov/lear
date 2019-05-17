<template>
  <header class="app-header" fixed app>
    <div class="container">
      <router-link to="/" class="navbar-brand">
        <img class="brand-img" src="@/assets/images/gov3_bc_logo.png"
          alt="Province of British Columbia Logo"
          title="Province of British Columbia"/>
      </router-link>
      <span class="paybc-logo" v-show="this.$route.name === 'PayBC'">Pay<strong>BC</strong></span>
    </div>
  </header>
</template>
<script>

export default {
  name: 'std-header'
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
      padding-top 0
      padding-bottom 0

  .brand-img
    margin-top 0.3rem

  .paybc-logo {
    margin-top 0.45rem
    margin-left 2rem
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
