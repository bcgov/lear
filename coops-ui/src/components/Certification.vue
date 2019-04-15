<template>
  <v-container>
    <v-checkbox
      v-model="checkbox1"
      color="primary"
      :label="'I certify that I have relevant knowledge of this business, and I am authorized to make this filing.'">
    </v-checkbox>
    <p>NOTE: It is an offence to make a false or misleading statement in respect of a material fact in a record submitted to the Corporate Registry for filing. </p>
  </v-container>
</template>

<script type="ts">
  export default {
    name: 'Certification',

    data () {
      return {
        checkbox1: true,
        checkbox2: false
      }
    }
  }
</script>

<style lang="stylus" scoped>
  .v-input--selection-controls
    margin-top 0

  p
    margin-bottom 0
    margin-left 2rem
    line-height 1.3rem
    font-size 0.875rem
</style>