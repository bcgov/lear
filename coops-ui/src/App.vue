<template>
  <div id="app">
    <std-header></std-header>
    <router-view/>
  </div>
</template>

<script>
import StdHeader from '@/components/StdHeader.vue'

export default {
  name: 'home',
  components: {
    StdHeader
  }
}
</script>

<style lang="stylus">
  @import "./assets/styles/base.styl";
  @import "./assets/styles/layout.styl";
</style>
