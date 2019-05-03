<template>
  <v-card>
    <header>Fee Summary</header>
    <v-slide-y-transition group tag="ul" class="fee-list">
      <li class="container fee-list__item" v-show="fee.name" v-for="fee in fees" :key="fee.id">
        <div class="fee-list__item-name">{{fee.name}}</div>
        <div class="fee-list__item-value">{{fee.value | currency}}</div>
      </li>
    </v-slide-y-transition>
    <div class="container fee-total">
      <div class="fee-total__name">Total Fees</div>
      <div class="fee-total__currency">CDN</div>
      <div class="fee-total__value">
        <v-slide-y-reverse-transition name="slide" mode="out-in">
          <div :key="totalFees">{{totalFees | currency}}</div>
        </v-slide-y-reverse-transition>
      </div>
    </div>
  </v-card>
</template>

<script>
export default {
  name: 'FeeSummary',

  data: () => ({
    fees: [
      {
        id: "annualReport",
        name: "Annual Report Filing",
        value: 30.00
      }
    ],
    addressFee: {
      id: 1,
      name: "Change Director Information",
      value: 15.00
    }
  }),

  methods: {
    addChangeAddressFee (index) {
      this.fees.push({ id: 2, name: "Change Registered Office Addresses", value: 15.00 });
    }
  },

  computed: {
    totalFees () {
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

.container
  display flex
  flex-flow row nowrap
  line-height 1.2rem
  font-size 0.875rem

.fee-list
  border-bottom 1px solid $gray3

.fee-list__item
  &-name,
  &-value
    font-weight 700

  &-name
    flex 1 1 auto
    margin-right 2rem

  &-value
    flex 0 0 auto
    text-align right

.fee-list__item + .fee-list__item
  border-top 1px solid $gray3

.fee-total
  align-items center
  letter-spacing -0.01rem
  line-height auto

  &__name
    flex 1 1 auto
    margin-right auto
    font-weight 700

  &__currency
    margin-right 0.5rem
    color $gray5
    font-weight 500

  &__value
    font-size 1.65rem
    font-weight 700

</style>