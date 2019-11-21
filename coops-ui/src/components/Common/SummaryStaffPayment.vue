<template>
  <v-card flat id="staff-payment-container">
    <div class="container">
      <div class="routingslipnumber-container">
        <label>
          <span>Routing Slip Number</span>
        </label>
        <div class="value routingslipnumber">
          <p>{{ value }}</p>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator'

@Component({})
export default class SummaryStaffPayment extends Vue {
  // Prop passed into this component.
  @Prop({ default: '' })
  private value: string
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';

#staff-payment-container {
  margin-top: 1rem;
  padding-bottom: 0.5rem;
  padding-top: 1rem;
  font-size: 0.875rem;
}

.routingslipnumber-container {
  display: flex;
  flex-flow: column nowrap;
  position: relative;

  > label:first-child {
    font-weight: 700;
  }
}

@media (min-width: 768px) {
  .routingslipnumber-container {
    flex-flow: row nowrap;

    > label:first-child {
      flex: 0 0 auto;
      padding-right: 2rem;
      width: 14rem;
    }
  }
}

.value.routingslipnumber {
  min-width: 35rem;
}
</style>
