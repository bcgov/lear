<template>
  <v-card flat>
    <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">

      <!---- Registered Office Section ---->
      <div class="address-edit-header"
        v-if="showAddressForm">
        <label class="address-edit-title">Registered Office</label>
      </div>
      <!-- Registered Delivery Address -->
      <li class="container">
        <div class="meta-container">
          <label v-if="!showAddressForm">Registered Office</label>
          <label v-else>Delivery Address</label>
          <div class="meta-container__inner">
            <label v-if="!showAddressForm"><strong>Delivery Address</strong></label>
            <div class="address-wrapper">
              <delivery-address
              :address="deliveryAddress"
              :editing="showAddressForm"
              :schema="addressSchema"
              @update:address="updateBaseAddress(deliveryAddress, $event)"
              @valid="isBaseAddressValid('deliveryAddress', $event)"
              />
            </div>
            <!-- Change and Reset btns -->
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
                >
                  Reset
                </v-btn>
              </div>
            </v-expand-transition>
          </div>
        </div>
      </li>

      <!-- Registered Mailing Address -->
      <li class="container">
        <div class="meta-container">
          <label v-if="showAddressForm">Mailing Address</label>
          <label v-else></label>
          <div class="meta-container__inner">
            <label
              v-if="!showAddressForm && !isSameWithoutProp(deliveryAddress, mailingAddress, 'actions')">
              <strong>Mailing Address</strong>
            </label>
            <div class="form__row">
              <v-checkbox
                class="inherit-checkbox"
                label="Same as Delivery Address"
                v-if="showAddressForm"
                v-model="inheritDeliveryAddress"
              />
            </div>
            <div class="address-wrapper"
             v-if="!isSameWithoutProp(deliveryAddress, mailingAddress, 'actions') || showAddressForm"
            >
              <mailing-address
                v-if="!showAddressForm || !inheritDeliveryAddress"
                :address="mailingAddress"
                :editing="showAddressForm"
                :schema="addressSchema"
                @update:address="updateBaseAddress(mailingAddress, $event)"
                @valid="isBaseAddressValid('mailingAddress', $event)"
              />
            </div>
            <span v-else>
              Mailing Address same as above
            </span>
          </div>
        </div>
      </li>

      <!---- Records Office Section ---->
      <div class="address-edit-header"
           v-if="showAddressForm">
        <label class="address-edit-title">Record Office</label>
          <v-checkbox
            class="records-inherit-checkbox"
            label="Same as Registered Office"
            v-if="showAddressForm"
            v-model="inheritRegisteredAddress"
          />
      </div>
      <div v-if="!isSameAddress(registeredAddress, recordsAddress) || !inheritRegisteredAddress">
        <!-- Records Delivery Address -->
        <li class="container">
          <div class="meta-container">
            <label v-if="!showAddressForm">Record Office</label>
            <label v-else>Delivery Address</label>
            <div class="meta-container__inner">
              <label v-if="!showAddressForm"><strong>Delivery Address</strong></label>
              <div class="address-wrapper">
                <delivery-address
                  :address="recDeliveryAddress"
                  :editing="showAddressForm"
                  :schema="addressSchema"
                  @update:address="updateBaseAddress(recDeliveryAddress, $event)"
                  @valid="isBaseAddressValid('recDeliveryAddress', $event)"
                />
              </div>
            </div>
          </div>
        </li>

        <!-- Records Mailing Address -->
        <li class="container">
          <div class="meta-container">
            <label v-if="showAddressForm">Mailing Address</label>
            <label v-else></label>
            <div class="meta-container__inner">
              <label
                v-if="!isSameWithoutProp(recDeliveryAddress, recMailingAddress, 'actions') && !showAddressForm">
                <strong>Mailing Address</strong>
              </label>
              <div class="form__row">
                <v-checkbox
                  class="inherit-checkbox"
                  label="Same as Delivery Address"
                  v-if="showAddressForm"
                  v-model="inheritRecDeliveryAddress"
                />
              </div>
              <div class="address-wrapper"
                   v-if="!isSameWithoutProp(recDeliveryAddress, recMailingAddress, 'actions') || showAddressForm"
              >
                <mailing-address
                  v-if="!showAddressForm || !inheritRecDeliveryAddress"
                  :address="recMailingAddress"
                  :editing="showAddressForm"
                  :schema="addressSchema"
                  @update:address="updateBaseAddress(recMailingAddress, $event)"
                  @valid="isBaseAddressValid('recMailingAddress', $event)"
                />
              </div>
              <span v-else>
                Mailing Address same as above
              </span>
            </div>
          </div>
        </li>
      </div>
      <div v-else>
        <li class="container" v-if="!showAddressForm">
          <div class="meta-container">
            <label>Record Office</label>
            <div class="meta-container__inner">
              <span>
                Same as Registered Office
              </span>
            </div>
          </div>
        </li>
      </div>

      <!---- Form Btn Section ---->
      <li>
        <div
          class="form__row form__btns"
          v-show="showAddressForm"
        >
          <v-btn
            class="update-btn"
            color="primary"
            id="reg-off-update-addr-btn"
            :disabled="!formValid"
            @click="updateAddress"
          >
            Update Addresses
          </v-btn>
          <v-btn id="reg-off-cancel-addr-btn" @click="cancelEditAddress">Cancel</v-btn>
        </div>
      </li>
    </ul>
  </v-card>
</template>

<script lang="ts">
// Libraries
import { Component, Emit, Prop, Watch, Mixins } from 'vue-property-decorator'
import isEmpty from 'lodash.isempty'

// Schemas
import { addressSchema } from '@/schemas'

// Components
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'

// Mixins
import { AddressMixin, CommonMixin } from '@/mixins'

// Interfaces
import { BaseAddressObjIF, BcorpAddressIf, AddressIF } from '@/interfaces/address-interfaces'

// Constants
import { ADDRESSCHANGED } from '@/constants'

@Component({
  components: {
    'delivery-address': BaseAddress,
    'mailing-address': BaseAddress
  }
})
export default class OfficeAddresses extends Mixins(AddressMixin, CommonMixin) {
    /**
     * Indicates whether the change button should be disabled or not
     */
    @Prop({ default: false })
    readonly changeButtonDisabled: boolean

    /**
     * Addresses object from the parent page.
     * If this is null then this is a new filing; otherwise these are the addresses from a draft filing.
     * This will be emitted back to the parent page when the addresses are updated.
     */
    @Prop({ default: null })
    readonly addresses: BcorpAddressIf | null

    // Init Store properties
    @Prop({ default: null })
    private registeredAddress: BaseAddressObjIF

    @Prop({ default: null })
    private recordsAddress: BaseAddressObjIF

    // The two addresses that come from the store. These are used to reset the address.
    private deliveryAddressOriginal: AddressIF | {} = {}
    private mailingAddressOriginal: AddressIF | {} = {}

    // The two addresses that come from the store. These are used to reset the address.
    private recDeliveryAddressOriginal: AddressIF | {} = {}
    private recMailingAddressOriginal: AddressIF | {} = {}

    // The two addresses that are the current state of the BaseAddress components.
    private deliveryAddress: AddressIF | {} = {}
    private mailingAddress: AddressIF | {} = {}

    // The two addresses that are the current state of the BaseAddress components.
    private recDeliveryAddress: AddressIF | {} = {}
    private recMailingAddress: AddressIF | {} = {}

    // The two addresses for Registered Office where the above are stored prior to an edit. These allow a cancel to
    // the address prior to edit, which if there was a prior edit will not be the data that originally
    // came from the store.
    private deliveryAddressTemp: AddressIF | {} = {}
    private mailingAddressTemp: AddressIF | {} = {}

    // The two addresses for Records Office where the above are stored prior to an edit. These allow a cancel to
    // the address prior to edit, which if there was a prior edit will not be the data that originally
    // came from the store.
    private recDeliveryAddressTemp: AddressIF | {} = {}
    private recMailingAddressTemp: AddressIF | {} = {}

    // Validation events from BaseAddress.
    private deliveryAddressValid: boolean = true
    private mailingAddressValid: boolean = true
    private recDeliveryAddressValid: boolean = true
    private recMailingAddressValid: boolean = true

    // Whether to show the editable forms for the addresses (true) or just the static display addresses (false).
    private showAddressForm: boolean = false

    // State of the checkbox for determining whether or not the mailing address is the same as the delivery address
    // For Registered Office
    private inheritDeliveryAddress: boolean = true

    // State of the checkbox for determining whether or not the mailing address is the same as the delivery address
    // For Records Office
    private inheritRecDeliveryAddress: boolean = true

    // State of the checkbox for determining whether the Record address is the same as the Registered address
    private inheritRegisteredAddress: boolean = true

    // The Address schema containing Vuelidate rules.
    private addressSchema: {} = addressSchema

    /**
     * Lifecycle callback to set up the component when it is mounted.
     */
    private mounted (): void {
      this.initAddresses()
      this.emitValid()
    }

    /**
     * Emits the modified state of the addresses.
     *
     * @returns a boolean that is true if an address has been modified, false otherwise.
     */
    @Emit('modified')
    private emitModified (): boolean {
      return this.modified
    }

    /**
     * Emits the valid state of the addresses.
     *
     * @returns a boolean that is true if the address data is valid, false otherwise.
     */
    @Emit('valid')
    private emitValid (): boolean {
      return this.formValid
    }

    /**
     * Emits updated addresses object to the parent page.
     */
    @Emit('update:addresses')
    private emitAddresses (): object {
      let deliveryAddressFinal: AddressIF | {} = Object.assign({}, this.deliveryAddress)
      let mailingAddressFinal: AddressIF | {} = Object.assign({}, this.mailingAddress)
      let recDeliveryAddressFinal: AddressIF | {} = Object.assign({}, this.recDeliveryAddress)
      let recMailingAddressFinal: AddressIF | {} = Object.assign({}, this.recMailingAddress)

      // if the address has changed from the original, set action flag
      this.addressModified(this.deliveryAddress, this.deliveryAddressOriginal)
        ? this.addAction(deliveryAddressFinal, ADDRESSCHANGED)
        : this.removeAction(deliveryAddressFinal, ADDRESSCHANGED)

      // if the address has changed from the original, set action flag
      this.addressModified(this.mailingAddress, this.mailingAddressOriginal)
        ? this.addAction(mailingAddressFinal, ADDRESSCHANGED)
        : this.removeAction(mailingAddressFinal, ADDRESSCHANGED)

      // if the address has changed from the original, set action flag
      this.addressModified(this.recDeliveryAddress, this.recDeliveryAddressOriginal)
        ? this.addAction(recDeliveryAddressFinal, ADDRESSCHANGED)
        : this.removeAction(recDeliveryAddressFinal, ADDRESSCHANGED)

      // if the address has changed from the original, set action flag
      this.addressModified(this.recMailingAddress, this.recMailingAddressOriginal)
        ? this.addAction(recMailingAddressFinal, ADDRESSCHANGED)
        : this.removeAction(recMailingAddressFinal, ADDRESSCHANGED)

      return {
        registeredOffice: {
          deliveryAddress: deliveryAddressFinal,
          mailingAddress: mailingAddressFinal
        },
        recordsOffice: {
          deliveryAddress: recDeliveryAddressFinal,
          mailingAddress: recMailingAddressFinal
        }
      }
    }

    /**
     * Called when addresses property changes (ie, when parent page has loaded a draft filing).
     */
    @Watch('addresses')
    onAddressesChanged (): void {
      this.deliveryAddress = isEmpty(this.addresses) ? {} : this.addresses.registeredOffice['deliveryAddress']
      this.mailingAddress = isEmpty(this.addresses) ? {} : this.addresses.registeredOffice['mailingAddress']

      this.recDeliveryAddress = isEmpty(this.addresses) ? {} : this.addresses.recordsOffice['deliveryAddress']
      this.recMailingAddress = isEmpty(this.addresses) ? {} : this.addresses.recordsOffice['mailingAddress']
    }

    /**
     * Computed value of whether or not the address form is valid.
     *
     * @returns a boolean that is true if the data on the form is valid, or false otherwise.
     */
    private get formValid (): boolean {
      return ((this.deliveryAddressValid && (this.inheritDeliveryAddress || this.mailingAddressValid)) &&
        (this.recDeliveryAddressValid && (this.inheritRecDeliveryAddress || this.recMailingAddressValid)))
    }

    /**
     * Computed value of whether or not an address has been modified from the original.
     *
     * @returns a boolean that is true if one or both addresses have been modified, or false otherwise.
     */
    private get modified (): boolean {
      return !(
        this.isSameAddress(this.deliveryAddress, this.deliveryAddressOriginal) &&
        this.isSameAddress(this.mailingAddress, this.mailingAddressOriginal) &&
        this.isSameAddress(this.recDeliveryAddress, this.recDeliveryAddressOriginal) &&
        this.isSameAddress(this.recMailingAddress, this.recMailingAddressOriginal))
    }

    /**
     * Computed value of whether or not the mailing address has been modified from the original.
     *
     * @returns a boolean that is true if the mailing address has been modified, or false otherwise.
     */
    private get mailingModified (): boolean {
      return !this.isSameAddress(this.mailingAddress, this.mailingAddressOriginal)
    }

    /**
     * Computed value of whether or not the address has been modified from the original.
     *
     * @returns a boolean that is true if the address has been modified, or false otherwise.
     */
    private addressModified (address: {}, addressOriginal: {}): boolean {
      return !this.isSameAddress(address, addressOriginal)
    }

    /**
     * Event callback to update the specified address when its component changes.
     *
     * @param baseAddress The base address that will be updated.
     * @param newAddress the object containing the new address.
     */
    private updateBaseAddress (baseAddress: AddressIF, newAddress: AddressIF): void {
      // Note that we do a copy of the fields (rather than change the object reference)
      // to prevent an infinite loop with the property.
      Object.assign(baseAddress, newAddress)
    }

    /**
     * Event callback to keep track of the validity of the address.
     *
     * @param valid a boolean indicating the validity of the address.
     */
    private isBaseAddressValid (addressToValidate: string, isValid: boolean): void {
      switch (addressToValidate) {
        case 'deliveryAddress': this.deliveryAddressValid = isValid
          break
        case 'mailingAddress': this.mailingAddressValid = isValid
          break
        case 'recDeliveryAddress': this.recDeliveryAddressValid = isValid
          break
        case 'recMailingAddress': this.recMailingAddressValid = isValid
          break
        default : console.log(`Error: Address- ${addressToValidate} not found`)
      }
      this.emitValid()
    }

    /**
     * Sets up the component for editing, retaining a copy of current state so that the user can cancel.
     */
    private editAddress (): void {
      this.inheritDeliveryAddress = this.isSameAddress(this.mailingAddress, this.deliveryAddress)
      this.inheritRecDeliveryAddress = this.isSameAddress(this.recMailingAddress, this.recDeliveryAddress)
      this.deliveryAddressTemp = { ...this.deliveryAddress }
      this.mailingAddressTemp = { ...this.mailingAddress }
      this.recDeliveryAddressTemp = { ...this.recDeliveryAddress }
      this.recMailingAddressTemp = { ...this.recMailingAddress }
      this.showAddressForm = true
    }

    /**
     * Cancels the editing of addresses, setting the addresses to the value they had before editing began.
     */
    private cancelEditAddress (): void {
      this.deliveryAddress = { ...this.deliveryAddressTemp }
      this.mailingAddress = { ...this.mailingAddressTemp }
      this.recDeliveryAddress = { ...this.recDeliveryAddressTemp }
      this.recMailingAddress = { ...this.recMailingAddressTemp }
      this.showAddressForm = false
    }

    /**
     * Updates the address data using what was entered on the forms.
     */
    private updateAddress (): void {
      // Inherit the mailing address for delivery address for Registered Office Addresses
      if (this.inheritDeliveryAddress) {
        this.mailingAddress = { ...this.deliveryAddress }
      }
      // Inherit the mailing address from delivery address for Records Office Addresses
      if (this.inheritRecDeliveryAddress) {
        this.recMailingAddress = { ...this.recDeliveryAddress }
      }
      // Inherit the Records Office addresses from Registered Office Addresses
      if (this.inheritRegisteredAddress) {
        this.recDeliveryAddress = { ...this.deliveryAddress }
        this.recMailingAddress = { ...this.mailingAddress }
      }

      this.showAddressForm = false
      this.emitAddresses()
      this.emitModified()
    }

    /**
     * Resets the address data to what it was before any edits were done.
     */
    private resetAddress (): void {
      this.deliveryAddress = { ...this.deliveryAddressOriginal }
      this.mailingAddress = { ...this.mailingAddressOriginal }
      this.recDeliveryAddress = { ...this.recDeliveryAddressOriginal }
      this.recMailingAddress = { ...this.recMailingAddressOriginal }
      this.emitAddresses()
      this.emitModified()
    }
    /**
     * Compares two address objects while omitting specified properties from the comparison.
     *
     * @param addressA The first address to compare
     * @param addressB The second address to compare
     * @param prop The property to omit during the comparison
     *
     * @return boolean A boolean indicating a match of addresses
     */
    private isSameWithoutProp (addressA: {}, addressB: {}, ...prop: Array<string>): boolean {
      return this.isSameAddress({ ...this.omitProp(addressA, [...prop]) }, { ...this.omitProp(addressB, [...prop]) })
    }

    /**
     * Add an action, if it doesn't already exist; ensures no multiples.
     */
    private addAction (address: AddressIF, val: string): void {
      if (address.actions.indexOf(val) < 0) address.actions.push(val)
    }

    /**
     * Remove an action, if it already exists.
     */
    private removeAction (address: AddressIF, val: string): void {
      address.actions = address.actions.filter(el => el !== val)
    }

    /**
     * Initialize Address Data
     *
     */
    private initAddresses (): void {
      // If loading loading from a draft filing
      if (this.addresses) {
        this.addresses.registeredOffice
          ? this.assignRegisteredAddresses(this.addresses.registeredOffice)
          : console.log('Registered Office not found')
        this.addresses.recordsOffice
          ? this.assignRegisteredAddresses(this.addresses.registeredOffice)
          : console.log('Records Office not found')
      } else {
        // If
        this.registeredAddress
          ? this.assignRegisteredAddresses(this.registeredAddress)
          : console.log('Registered Office not found')
        this.recordsAddress
          ? this.assignRecordAddresses(this.recordsAddress)
          : console.log('Records Office not found')
      }

      // emit address data back up so that parent data has data (needed for AR filing specifically)
      this.emitAddresses()
    }

    /**
     * Assign the Registered address objects actions and omit the addressType
     *
     */
    private assignRegisteredAddresses (addressBase: BaseAddressObjIF): void {
    // Assign Delivery Address
      const deliveryAddress = addressBase.deliveryAddress
      if (deliveryAddress) {
        deliveryAddress.actions = []
        this.deliveryAddressOriginal = { ...this.omitProp(deliveryAddress, ['addressType']) }
        if (isEmpty(this.deliveryAddress)) {
          this.deliveryAddress = { ...this.omitProp(deliveryAddress, ['addressType']) }
        }
      } else {
        console.log('invalid Delivery Address =', addressBase)
      }

      // Assign Mailing Address
      const mailingAddress = addressBase.mailingAddress
      if (mailingAddress) {
        mailingAddress.actions = []
        this.mailingAddressOriginal = { ...this.omitProp(mailingAddress, ['addressType']) }
        if (isEmpty(this.mailingAddress)) {
          this.mailingAddress = { ...this.omitProp(mailingAddress, ['addressType']) }
        }
      } else {
        console.log('invalid Mailing Address =', addressBase)
      }
    }

    /**
     * Assign the Registered address objects actions and omit the addressType
     *
     */
    private assignRecordAddresses (addressBase: BaseAddressObjIF): void {
    // Assign Delivery Address
      const deliveryAddress = addressBase.deliveryAddress
      if (deliveryAddress) {
        deliveryAddress.actions = []
        this.recDeliveryAddressOriginal = { ...this.omitProp(deliveryAddress, ['addressType']) }
        if (isEmpty(this.recDeliveryAddress)) {
          this.recDeliveryAddress = { ...this.omitProp(deliveryAddress, ['addressType']) }
        }
      } else {
        console.log('invalid Delivery Address =', addressBase)
      }

      // Assign Mailing Address
      const mailingAddress = addressBase.mailingAddress
      if (mailingAddress) {
        mailingAddress.actions = []
        this.recMailingAddressOriginal = { ...this.omitProp(mailingAddress, ['addressType']) }
        if (isEmpty(this.recMailingAddress)) {
          this.recMailingAddress = { ...this.omitProp(mailingAddress, ['addressType']) }
        }
      } else {
        console.log('invalid Mailing Address =', addressBase)
      }
    }
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
    margin-top: 1rem;
  }

  label:first-child {
    font-weight: 700;
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
      margin-top: 0;
    }
  }

  .address-list .form {
    margin-top: 1rem;
  }

  @media (min-width: 768px) {
    .address-list .form {
      margin-top: 0rem
    }
  }

  // Address Block Layout
  .address-wrapper{
    margin-top: .5rem;
  }

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
    display: flex;
    justify-content: flex-end;
    padding: 1rem;

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
  .records-inherit-checkbox {
    margin-top: 0rem;
    margin-left: 6rem;
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

  // Editing Address Form

  .address-edit-header {
    display: flex;
    background-color: rgba(1,51,102,0.15);
    padding: 1.25rem;

    address-edit-title {
      font-size: 16px;
      font-weight: bold;
      line-height: 22px;
    }
  }

</style>
