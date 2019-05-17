<template>
  <div>
    <EntityInfo/>
    <v-btn color="primary" large to="/AnnualReport">File</v-btn>
  </div>
</template>

<script lang='ts'>
  import { Component, Vue } from 'vue-property-decorator'
  import EntityInfo from '@/components/EntityInfo.vue'

  export default {
    name: "Dashboard",
    components: {
      EntityInfo,
    }
  }
</script>