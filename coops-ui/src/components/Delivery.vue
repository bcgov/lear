<template>
  <v-container>
    <ul>
      <li>
        <label>
          <span>Delivery Email Address</span>
        </label>
        <div class="value">
          <v-text-field solo flat label="Delivery Email Address" hint="Delivery Email Address Hint" persistent-hint="true"></v-text-field>
        </div>
      </li>
    </ul>
  </v-container>
</template>

<script type="ts">
export default {
  name: 'Delivery'
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .theme--light.v-text-field--solo>.v-input__control>.v-input__slot
    border 1px solid $gray5
</style>
