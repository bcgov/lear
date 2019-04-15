<template>
  <div class="form">
    <h4>Change Delivery Address</h4>
    <!--
    <v-alert type="primary" :value="true">
      Changing Registered Office Addresses is an additional fee.
    </v-alert>
    -->
    <div class="form__row">
      <v-text-field box label="Start typing an address"></v-text-field>
    </div>
    <div class="form__row">
      <v-text-field box label="Address"></v-text-field>
    </div>
    <div class="form__row">
      <v-text-field box label="Special Instructions"></v-text-field>
    </div>
    <div class="form__row form__btns">
      <v-btn color="primary" @click="cancelEditAddress1">Update Address</v-btn>
      <v-btn @click="cancelEditAddress1">Cancel</v-btn>
    </div>
  </div>
</template>

<script type="ts">
export default {
  name: 'EditAddress'
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"
</style>
