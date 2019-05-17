<template>
  <div>
    <v-btn color="primary" large to="/Dashboard">Dashboard</v-btn>
  </div>

</template>

<script lang='ts'>
  import { Component, Vue } from 'vue-property-decorator'
  import FeeSummary from '@/components/FeeSummary.vue'
  export default {
    name: "Payment",
    components: {
      FeeSummary
    },
    data () {
      return {
      }
    }
  }
</script>