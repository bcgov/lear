<template>
  <v-card flat>
    <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">
      <!-- Registered Office Addresses-->

      <!-- Delivery Address -->
      <li class="container">
        <div class="meta-container">
          <label>Registered Office</label>
          <div class="meta-container__inner">
            <label>Delivery Address</label>
            <BaseAddress
              :address="registeredAddress.deliveryAddress"
              :editing="showAddressForm"
            />
<!--            <delivery-address-->
<!--              :address="regDeliveryAddress"-->
<!--              :editing="showAddressForm"-->
<!--              :schema="addressSchema"-->
<!--              v-on:update:address="updateDelivery($event)"-->
<!--              @valid="isDeliveryValid"-->
<!--            />-->
            <v-expand-transition>
              <div class="address-block__actions">
                <v-btn
                  color="primary"
                  text
                  id="reg-off-addr-change-btn"
                  small
                  v-if="!showAddressForm"
                  :disabled="changeButtonDisabled"
                  @click="editAddress"
                >
                  <v-icon small>mdi-pencil</v-icon>
                  <span>Change</span>
                </v-btn>
                <br />
                <v-btn
                  class="reset-btn"
                  color="red"
                  id="reg-off-addr-reset-btn"
                  outlined
                  small
                  v-if="!showAddressForm && modified"
                  @click="resetAddress"
                >Reset</v-btn>
              </div>
            </v-expand-transition>
          </div>
        </div>
      </li>

      <!-- Mailing Address -->
      <li class="container">
        <div class="meta-container">
          <label></label>
          <div class="meta-container__inner">
            <label>Mailing Address</label>
            <div class="form__row">
              <v-checkbox
                class="inherit-checkbox"
                label="Same as Delivery Address"
                v-if="showAddressForm"
                v-model="inheritDeliveryAddress"
              ></v-checkbox>
            </div>
              <BaseAddress
                :address="registeredAddress.mailingAddress"
                :editing="showAddressForm"
              />
<!--            <mailing-address-->
<!--              v-if="!showAddressForm || !inheritDeliveryAddress"-->
<!--              :address="regMailingAddress"-->
<!--              :editing="showAddressForm"-->
<!--              :schema="addressSchema"-->
<!--              v-on:update:address="updateMailing($event)"-->
<!--              @valid="isMailingValid"-->
<!--            />-->
          </div>
        </div>
      </li>

      <!-- Records Office Addresses Bcorps-->

<!--      &lt;!&ndash; Delivery Address &ndash;&gt;-->
<!--      <div>-->
<!--        <li class="container">-->
<!--          <div class="meta-container">-->
<!--            <label>Records Office</label>-->
<!--            <div class="meta-container__inner">-->
<!--              <label>Delivery Address</label>-->
<!--              <delivery-address-->
<!--                :address="recDeliveryAddress"-->
<!--                :editing="showAddressForm"-->
<!--                :schema="addressSchema"-->
<!--                v-on:update:address="updateDelivery($event)"-->
<!--                @valid="isDeliveryValid"-->
<!--              />-->
<!--            </div>-->
<!--          </div>-->
<!--        </li>-->

<!--        &lt;!&ndash; Mailing Address &ndash;&gt;-->
<!--        <li class="container">-->
<!--          <div class="meta-container">-->
<!--            <label></label>-->
<!--            <div class="meta-container__inner">-->
<!--              <label>Mailing Address</label>-->
<!--              <div class="form__row">-->
<!--                <v-checkbox-->
<!--                  class="inherit-checkbox"-->
<!--                  label="Same as Delivery Address"-->
<!--                  v-if="showAddressForm"-->
<!--                  v-model="inheritDeliveryAddress"-->
<!--                ></v-checkbox>-->
<!--              </div>-->
<!--              <mailing-address-->
<!--                v-if="!showAddressForm || !inheritDeliveryAddress"-->
<!--                :address="recMailingAddress"-->
<!--                :editing="showAddressForm"-->
<!--                :schema="addressSchema"-->
<!--                v-on:update:address="updateMailing($event)"-->
<!--                @valid="isMailingValid"-->
<!--              />-->
<!--            </div>-->
<!--          </div>-->
<!--        </li>-->
<!--      </div>-->

      <!-- Submission Button row -->
<!--      <li class="container">-->
<!--        <div-->
<!--          class="form__row form__btns"-->
<!--          v-show="showAddressForm"-->
<!--        >-->
<!--          <v-btn-->
<!--            class="update-btn"-->
<!--            color="primary"-->
<!--            id="reg-off-update-addr-btn"-->
<!--            :disabled="!formValid"-->
<!--            @click="updateAddress"-->
<!--          >Update Addresses</v-btn>-->
<!--          <v-btn id="reg-off-cancel-addr-btn" @click="cancelEditAddress">Cancel</v-btn>-->
<!--        </div>-->
<!--      </li>-->
    </ul>
  </v-card>
</template>
<script lang="ts">
// Libraries
import { Component, Prop, Mixins } from 'vue-property-decorator'
import { mapState } from 'vuex'

// Components
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'

// Mixins
import { AddressMixin, CommonMixin } from '@/mixins'

@Component({
  components: {
    BaseAddress
  },
  computed: {
    ...mapState(['registeredAddress', 'recordsAddress'])
  }
})
export default class OfficeAddress extends Mixins(AddressMixin, CommonMixin) {
  /**
   * Addresses object from the parent page.
   * If this is null then this is a new filing; otherwise these are the addresses from a draft filing.
   * This will be emitted back to the parent page when the addresses are updated.
   */
  @Prop({ default: null })
  readonly addresses: object

  /**
   * Indicates whether the change button should be disabled or not
   */
  @Prop({ default: false })
  readonly changeButtonDisabled: boolean

  // Init Store properties
  private registeredAddress: object
  // private recordsAddress: object

  // Whether to show the editable forms for the addresses (true) or just the static display addresses (false).
  private showAddressForm: boolean = false

  // State of the form checkbox for determining whether or not the mailing address is the same as the delivery address.
  private inheritDeliveryAddress: boolean = true

  mounted (): void {
    console.log(this.registeredAddress)
  }

//   /**
//    * Updates the address data using what was entered on the forms.
//    */
//   private updateAddress (): void {
//     if (this.inheritDeliveryAddress) {
//       this.mailingAddress = { ...this.deliveryAddress }
//     }
//     this.showAddressForm = false
//     this.emitAddresses()
//     this.emitModified()
//   }
//
//   /**
//    * Init Address Data
//    *
//    */
//   private initAddresses (): void {
//       this.registeredAddress.deliveryAddress.actions = []
//
//       this.deliveryAddressOriginal = { ...this.omitProp(deliveryAddress, ['addressType']) }
//       // If parent page loaded draft before this API call, don't overwrite draft delivery address.
//       // Otherwise this API call finished before parent page loaded draft, or parent page won't
//       // load draft (ie, this is a new filing) -> initialize delivery address.
//       if (isEmpty(this.deliveryAddress)) {
//           this.deliveryAddress = { ...this.omitProp(deliveryAddress, ['addressType']) }
//       }
//   } else {
//     console.log('loadAddressesFromApi() error - invalid Delivery Address =', deliveryAddress)
// }
//   }
}

</script>
<style lang="scss" scoped>
  @import '../../assets/styles/theme.scss';

  .v-btn {
    margin: 0;
    min-width: 6rem;
    text-transform: none;
  }

  .reset-btn {
    margin-top: 0.5rem;
  }

  .meta-container {
    display: flex;
    flex-flow: column nowrap;
    position: relative;
  }

  .meta-container__inner {
    margin-top: 0rem;
  }

  label:first-child {
    font-weight: 500;
  &__inner {
     flex: 1 1 auto;
   }
  }

  @media (min-width: 768px) {
    .meta-container {
      flex-flow: row nowrap;

    label:first-child {
      flex: 0 0 auto;
      padding-right: 4rem;
      width: 12rem;
    }
  }
  .meta-container__inner {
    margin-top: 0rem;
  }
  }

  .address-list .form {
    margin-top: 1rem;
  }

  @media (min-width: 768px) {
    .address-list .form {
      margin-top: 0;
    }
  }

  // Address Block Layout
     .address-block__actions {
       position: absolute;
       top: 0;
       right: 0;

  .v-btn {
    min-width: 4rem;
  }

  .v-btn + .v-btn {
    margin-left: 0.5rem;
  }
  }

  // Form Row Elements
     .form__row + .form__row {
       margin-top: 0.25rem;
     }

  .form__btns {
    text-align: right;

  .v-btn {
    margin: 0;

  + .v-btn {
    margin-left: 0.5rem;
  }
  }
  }

  .form__row.three-column {
    display: flex;
    flex-flow: row nowrap;
    align-items: stretch;
    margin-right: -0.5rem;
    margin-left: -0.5rem;
  }

  .inherit-checkbox {
    margin-top: -3px;
    margin-left: -3px;
    padding: 0;
  }

  // Registered Office Address Form Behavior
     .show-address-form {
  li:first-child {
    padding-bottom: 0;
  }
  }

  ul {
    margin: 0;
    padding: 0;
    list-style-type: none;
  }

</style>
