<template>
  <v-card>
    <header>Fee Summary</header>
    <ul>
      <li class="container" v-for="fee in fees" v-bind:key="fee.id">
        <div class="fee-name">{{fee.name}}</div>
        <div class="fee-value">${{fee.value}}</div>
      </li>
      <li class="container summary">
        <div class="fee-name">Total Fees</div>
        <div class="fee-currency">CDN</div>
        <div class="fee-value">
          ${{totalFees}}</div>
      </li>
    </ul>
  </v-card>
</template>

<script>
export default {
  name: 'FeeSummary',

  data: () => ({
    fees: [
      {name: "Annual Report Filing", value: 40.00},
      {name: "Update Director Information", value: 15.00},
      {name: "Update Registered Office Addresses", value: 15.00}
    ]
  }),

  computed: {
    totalFees() {
      return this.fees.reduce((acc, item) => acc + item.value, 0);
    },
  },
};
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  header
    padding 1rem 1.25rem
    color #fff
    background $BCgovBlue5
    font-weight 700

  ul
    li + li
      border-top 1px solid $gray3

  .container
    display flex
    flex-flow row nowrap
    line-height 1.2rem
    font-size 0.875rem

  .fee-name,
  .fee-value
    font-weight 700

  .fee-name
    flex 1 1 auto
    margin-right 2rem

  .fee-value
    flex 0 0 auto
    text-align right

  .summary
    align-items center
    letter-spacing -0.01rem
    line-height auto

    .fee-currency
      margin-right 0.5rem
      color $gray5
      font-weight 500

    .fee-value
      font-size 1.65rem

</style>