<template>
  <v-container class="view-container">
      <article id="example-content">
        <header>
          <h1>Your Cart: <small>Review the items in your Cart before proceeding to payment.</small></h1>
        </header>
        <v-alert color="success" :value="true">
          You have added 1 items to your Cart. Review these items before proceeding to payment.
        </v-alert>
        <section>
          <header>
            <h2>Credit Card Cart</h2>
          </header>
        </section>
        <div>
          <table class="payment-table">
            <thead>
              <tr>
                <th>Ref.No.</th>
                <th class="no-wrap">CL #</th>
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
                <td>#11</td>
                <td>n/a</td>
                <td>My Business Name</td>
                <td>123456789</td>
                <td>11728</td>
                <td>BC Registries Co-op Filings</td>
                <td>{{ date | moment }}</td>
                <td>
                  <div>
                     $70.00
                  </div>
                </td>
                <td>$70.00</td>
                <td>
                  <div class="form-input">
                    <div class="prefix">$</div>
                    <input type="number" class="payment-input" value="70.00" disabled/>
                  </div>
                </td>
                <td>
                  Credit
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="11" class="payment-buttons-row">
                  <div class="flex-row">
                    <v-btn color="info" to="/Payment">Add more Quick Pay Items</v-btn>
                    <v-btn class="last-btn" color="success" to="/Dashboard">Proceed to Credit Cart Payment</v-btn>
                  </div>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
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
    },

    methods: {
      moment: function () {
        return moment();
      }
    },

    filters: {
      moment: function (date) {
        return moment(date).format('YYYY/DD/MM');
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

  h1 small
    vertical-align middle
    color $gray7
    font-size 1rem
    font-weight 400

  section header
    margin-bottom 1rem
    padding 0.5rem 1rem
    color #ffffff
    background $BCgovBlue4

    h2
      margin 0
      font-size 1.25rem
      font-weight 400

    .v-icon
      vertical-align middle
      margin-top -4px
      margin-right 0.5rem
      color $BCgovGold5

  .payment-buttons-row
    padding-top 1rem
    padding-bottom 1rem

  .align-right
    text-align right

  .info-row
    .v-icon
      margin-right 0.25rem

  .v-alert
    margin-top 2.5rem
    padding-top 2rem
    padding-bottom 2rem
    border none
    text-align center

  .flex-row
    display flex

  .last-btn
    margin-left auto

  .payment-amount-column
    width 10rem

  .payment-type-column
    width 10rem
</style>