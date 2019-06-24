<template>
  <v-container class="view-container">
    <article id="example-content">
      <header>
        <h1>Your Cart: <small>Review the items in your Cart before proceeding to payment.</small></h1>
      </header>
      <v-alert color="success" :value="true">
        You have added 1 items to your Cart. Review these items before proceeding to payment.
      </v-alert>
      <section class="payment-section">
        <header>
          <h2>Credit Card Cart</h2>
          <span class="header-total">
            <label>Total:</label>
            <strong>$ 70.00</strong>
            <small>(1 items)</small>
          </span>
        </header>
        <div class="payment-table-container">
          <table class="payment-table">
            <thead>
              <tr>
                <th>Ref.No.</th>
                <th class="no-wrap">C.I. #</th>
                <th>Customer Name</th>
                <th class="no-wrap">Customer #</th>
                <th>Invoice #</th>
                <th>Invoice Type</th>
                <th>Invoice Due Date</th>
                <th>Original Amount</th>
                <th>Outstanding Amount</th>
                <th class="payment-amount-column">Payment Amount</th>
                <th>Payment Type</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td></td>
                <td>n/a</td>
                <td>Pathfinder Cooperative</td>
                <td>105023337BC0157</td>
                <td>11780</td>
                <td>BC Registries Co-op Filings</td>
                <td>{{moment(date).format('YYYY/MM/DD')}}</td>
                <td>
                  <div>
                    $70.00
                  </div>
                </td>
                <td>$70.00</td>
                <td>
                  <div class="form-input ">
                    <div class="prefix">$</div>
                    <input type="number" class="payment-input" value="70.00" disabled/>
                  </div>
                </td>
                <td>
                  Credit
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <footer>
          <v-btn class="add-more-btn" color="info" depressed to="/Payment"><v-icon small>search</v-icon>Add more Quick Pay Items</v-btn>
          <div class="checkout-info">
            <label>Total:</label>
            <div class="form-input">
              <div class="prefix">$</div>
              <input type="number" class="payment-input" value="70.00" disabled/>
            </div>
            <v-btn class="checkout-btn" color="success" depressed to="/PaymentInfo">Proceed to Credit Card Payment</v-btn>
          </div>
        </footer>
      </section>
    </article>
  </v-container>
</template>

<script lang='ts'>
  import { Component, Vue } from 'vue-property-decorator'
  import moment from 'moment'

  Vue.prototype.moment = moment

  export default {
    name: "PaymentCart",

    data () {
      return {
      }
    }
  }
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .view-container
    padding-right 2rem
    padding-left 2rem
    background #ffffff

  section header
    display flex
    padding 0.5rem 1rem
    color #ffffff
    background $BCgovBlue4

    h2
      margin 0
      font-size 1.25rem
      font-weight 500

  .header-total
    display flex
    align-items center
    margin-left auto

    label
      font-size 0.85rem

    strong
      margin-right 0.5rem
      margin-left 0.5rem
      font-size 1.25rem
      font-weight 500

    .v-icon
      vertical-align middle
      margin-top -4px
      margin-right 0.5rem
      color $BCgovGold5

  section footer
    display flex
    padding 1rem
    background $gray1
    font-size 0.8rem

  h1 small
    vertical-align middle
    color $gray7
    font-size 1rem
    font-weight 400

  .v-alert
    margin-top 2.5rem
    padding-top 2rem
    padding-bottom 2rem
    border none
    text-align center

  .add-more-btn
    .v-icon
      margin-right 0.5rem

  .checkout-info
    display flex
    align-items center
    margin-left auto

    label
      margin-right 0.5rem
      font-weight 400

    .form-input
      height 36px

  .checkout-btn
    border-top-left-radius 0
    border-bottom-left-radius 0
</style>