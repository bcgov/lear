<template>
  <v-container class="payment-info view-container">
    <v-card>
      <v-card-title>
        Enter Payment Information
      </v-card-title>
      <v-card-text>
        <div class="cc-form__row">
          <label>Invoice/Order Number:</label>
          <div class="value-static">
            11700
          </div>
        </div>
        <div class="cc-form__row">
          <label>Amount:</label>
          <div class="value-static">
            $70.00
          </div>
        </div>
        <div class="cc-form__row">
          <label>Credit Card Type:</label>
          <div class="value">
            <select class="proto-select">
              <option selected="selected">VISA</option>
              <option>MasterCard</option>
              <option>American Express</option>
            </select>
          </div>
        </div>
        <div class="cc-form__row">
          <label>Credit Card Number</label>
          <div class="value">
            <input type="text" class="cc-number proto-input" />
          </div>
        </div>
        <div class="cc-form__row">
          <label>Expriation Date</label>
          <div class="value">
            <select class="proto-select">
              <option selected="selected">01</option>
            </select>
            <span> / </span>
            <select class="proto-select">
              <option selected="selected">2019</option>
            </select>
          </div>
        </div>
        <div class="cc-form__row">
          <label>Credit Card CVD:</label>
          <div class="value">
            <input type="text" class="cvd-input proto-input" />
          </div>
        </div>
        <div class="cc-form__row cc-form__btns">
          <v-btn color="warning" depressed to="/PaymentCart">Cancel & return to PayBC</v-btn>
          <v-btn outline depressed to="/DashboardSuccess">Submit Payment</v-btn>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator'

  export default {
    name: "Payment Information"
  }
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .v-card
    margin 0 auto
    width 38rem

  .v-card__title
    justify-content center
    padding 0.75rem 1rem
    color #ffffff
    background $BCgovBlue4
    font-size 1.5rem
    font-weight 500

  .v-card__text
    padding 1.25rem
    padding-top 2rem
    line-height 1rem
    font-size 0.875rem
    font-weight 500

  .cc-form__row
    display flex
    align-items center

    + .cc-form__row
      margin-top 0.5rem

    label
      flex 0 0 10rem

    .value
      flex 1 1 auto

    .value-static
      flex 1 1 auto
      padding-top 0.5rem
      padding-bottom 0.5rem

  .proto-input,
  .proto-select
    height 36px
    padding 0.5rem
    border 1px solid $gray5

  .proto-select
    -webkit-appearance menulist

  .cc-number
    width 100%

  .cvd-input
    width 4rem

  .cc-form__btns
    padding-top 1rem
    justify-content center

</style>