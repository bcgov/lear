<template>
  <v-container class="view-container">
    <article id="example-content">
      <header>
        <h1>Annual Report Filing Payment</h1>
        <!--
        <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.</p>
        -->
      </header>
      <section class="payment-section">
        <header>
          <h2><v-icon>check_circle</v-icon>Your Invoice</h2>
        </header>
        <div class="payment-table-container">
          <table class="payment-table">
            <thead>
              <tr>
                <th class="checkbox-column"></th>
                <th>Invoice Number</th>
                <th>Customer Name</th>
                <th>Customer Number</th>
                <th>Invoice Due Date</th>
                <th class="payment-amount-column">Payment Amount</th>
                <th class="payment-type-column">Payment Type</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="checkbox-column">
                  <input type="checkbox" checked disabled/>
                </td>
                <td>11780</td>
                <td>Pathfinder Cooperative</td>
                <td>105023337BC0157</td>
                <td>
                  <div>
                    {{moment(date).format('YYYY/MM/DD')}}
                  </div>
                </td>
                <td>
                  <div class="form-input">
                    <div class="prefix">$</div>
                    <input type="number" class="payment-input" value="70.00" disabled/>
                  </div>
                </td>
                <td>
                  <div class="form-input">
                    <select disabled>
                      <option selected="selected">Credit</option>
                    </select>
                  </div>
                </td>
              </tr>
              <tr class="info-row">
                <td colspan="7" class="align-right"><v-icon small>info</v-icon>Payment Types that are not supported by an invoice will not be available in the Payment Type list.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <footer>
          <v-btn color="primary" class="add-item-btn" depressed to="/PaymentCart">Add Invoice(s) to your Cart</v-btn>
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
  name: "Payment"
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .view-container
    padding-right 2rem
    padding-left 2rem
    background #ffffff

  section header
    padding 0.5rem 1rem
    color #ffffff
    background $BCgovBlue4

    h2
      margin 0
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

  .checkbox-column
    width 3rem
    text-align center

    input
      margin-top 4px

  .info-row
    .v-icon
      margin-right 0.25rem

  .add-item-btn
    margin-left auto

</style>
