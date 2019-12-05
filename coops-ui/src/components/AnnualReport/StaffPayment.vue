<template>
  <v-card flat id="AR-step-5-container">
    <v-form class="staff-payment-container" v-model="formValid">
      <div class="routingslipnumber-container">
        <label>Routing Slip Number</label>
        <div class="value routingslipnumber">
          <v-text-field
            filled
            persistent-hint
            id="routing-slip-number-textfield"
            label="Enter the Routing Slip Number "
            hint="Fee Accounting System Routing Slip Number (9 digits)"
            v-model="routingSlipNumber"
            :rules="rules"
          />
        </div>
      </div>
    </v-form>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop, Watch, Emit } from 'vue-property-decorator'

@Component({})
export default class StaffPayment extends Vue {
  // Prop passed into this component.
  @Prop({ default: null })
  private value: string

  private formValid : boolean = false

  // Local copy of the prop, initialized to initial prop value.
  private routingSlipNumber: string = this.value

  // Vuetify rules, used for error messages and styling.
  private readonly rules = [
    v => !!v || 'Routing Slip Number is required',
    v => /^\d{9}$/.test(v) || 'Routing Slip Number must be 9 digits'
  ]

  // Notifies parent of initial state.
  private created (): void {
    this.emitUpdateValue(this.routingSlipNumber)
    this.emitValid(this.formValid)
  }

  // Watches for change to prop and updates local copy.
  @Watch('value')
  private onValueChanged (val: string): void {
    this.routingSlipNumber = val
  }

  // Watches for change to Routing Slip Number and notifies parent.
  @Watch('routingSlipNumber')
  private onRoutingSlipNumberChanged (val: string): void {
    this.emitUpdateValue(this.routingSlipNumber)
  }

  // Watches for change to form validity and notifies parent.
  @Watch('formValid')
  private onValidChanged (val: boolean): void {
    this.emitValid(this.formValid)
  }

  // Emits an event to inform parent of new Routing Slip Number.
  @Emit('update:value')
  private emitUpdateValue (val: string): void { }

  // Emits an event to inform parent of new validity.
  @Emit('valid')
  private emitValid (val: boolean): void { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';

#AR-step-5-container {
  margin-top: 1rem;
  padding-bottom: 0.5rem;
  padding-top: 1rem;
  line-height: 1.2rem;
  font-size: 0.875rem;
}

.staff-payment-container {
  padding: 1.25rem;
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
      width: 12rem;
    }
  }
}

.value.routingslipnumber {
  min-width: 35rem;
}
</style>
