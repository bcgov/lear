<template>
  <div id="office-addresses">
    <v-card flat>
      <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">
        <!-- Registered Office Section -->
        <div class="address-edit-header" v-if="showAddressForm">
          <label class="address-edit-title">Registered Office</label>
        </div>

        <!-- Registered Delivery Address -->
        <li class="address-list-container">
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
                  @valid="updateAddressValid('deliveryAddress', $event)"
                />
              </div>

              <!-- Change and Reset Buttons -->
              <v-expand-transition>
                <div class="address-block__actions">
                  <v-btn
                    color="primary"
                    text
                    id="reg-off-addr-change-btn"
                    small
                    v-if="!showAddressForm"
                    :disabled="!componentEnabled"
                    @click="editAddress()"
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
                    @click="resetAddress()"
                  >
                    <span>Reset</span>
                  </v-btn>
                </div>
                </v-expand-transition>
            </div>
          </div>
        </li>

        <!-- Registered Mailing Address -->
        <li class="address-list-container">
          <div class="meta-container">
            <label>{{ showAddressForm ? "Mailing Address" : "" }}</label>
            <div class="meta-container__inner">
              <label v-if="!showAddressForm && !isSame(deliveryAddress, mailingAddress, 'actions')">
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
                v-if="!isSame(deliveryAddress, mailingAddress, 'actions') || showAddressForm"
              >
                <mailing-address
                  v-if="!showAddressForm || !inheritDeliveryAddress"
                  :address="mailingAddress"
                  :editing="showAddressForm"
                  :schema="addressSchema"
                  @update:address="updateBaseAddress(mailingAddress, $event)"
                  @valid="updateAddressValid('mailingAddress', $event)"
                />
              </div>
              <span v-else id="sameAsAbove">Mailing Address same as above</span>
            </div>
          </div>
        </li>

        <div v-if="entityFilter(EntityTypes.BCOMP)">
          <div class="address-edit-header" v-if="showAddressForm">
            <label class="address-edit-title">Records Office</label>
            <v-checkbox
              class="records-inherit-checkbox"
              label="Same as Registered Office"
              v-if="showAddressForm"
              v-model="inheritRegisteredAddress"
            />
          </div>

          <div v-if="!inheritRegisteredAddress">
            <!-- Records Delivery Address -->
            <li class="address-list-container">
              <div class="meta-container">
                <label v-if="!showAddressForm">Records Office</label>
                <label v-else>Delivery Address</label>

                <div class="meta-container__inner">
                  <label v-if="!showAddressForm"><strong>Delivery Address</strong></label>
                  <div class="address-wrapper">
                    <delivery-address
                      :address="recDeliveryAddress"
                      :editing="showAddressForm"
                      :schema="addressSchema"
                      @update:address="updateBaseAddress(recDeliveryAddress, $event)"
                      @valid="updateAddressValid('recDeliveryAddress', $event)"
                    />
                  </div>
                </div>
              </div>
            </li>

            <!-- Records Mailing Address -->
            <li class="address-list-container">
              <div class="meta-container">
                <label>{{ showAddressForm ? "Mailing Address" : "" }}</label>
                <div class="meta-container__inner">
                  <label v-if="!isSame(recDeliveryAddress, recMailingAddress, 'actions') && !showAddressForm">
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
                      v-if="!isSame(recDeliveryAddress, recMailingAddress, 'actions') || showAddressForm"
                  >
                    <mailing-address
                      v-if="!showAddressForm || !inheritRecDeliveryAddress"
                      :address="recMailingAddress"
                      :editing="showAddressForm"
                      :schema="addressSchema"
                      @update:address="updateBaseAddress(recMailingAddress, $event)"
                      @valid="updateAddressValid('recMailingAddress', $event)"
                    />
                  </div>
                  <span v-else>Mailing Address same as above</span>
                </div>
              </div>
            </li>
          </div>

          <div v-else>
            <li class="address-list-container" v-if="!showAddressForm">
              <div class="meta-container">
                <label>Records Office</label>
                <div class="meta-container__inner">
                  <span id="sameAsRegistered">Same as Registered Office</span>
                </div>
              </div>
            </li>
          </div>
        </div>

        <!-- Form Button Section -->
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
              @click="updateAddress()"
            >
              <span>Update Addresses</span>
            </v-btn>
            <v-btn id="reg-off-cancel-addr-btn" @click="cancelEditAddress()">Cancel</v-btn>
          </div>
        </li>
      </ul>
    </v-card>
  </div>
</template>

<script lang="ts">
// Libraries
import { Component, Emit, Prop, Watch, Mixins } from 'vue-property-decorator'
import { isEmpty } from 'lodash'

// Schemas
import { officeAddressSchema } from '@/schemas'

// Components
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'

// Mixins
import { CommonMixin, EntityFilterMixin } from '@/mixins'

// Interfaces
import { BaseAddressObjIF, BcorpAddressIf, AddressIF } from '@/interfaces'

// Constants
import { ADDRESSCHANGED } from '@/constants'

// Enums
import { EntityTypes } from '@/enums'

@Component({
  components: {
    'delivery-address': BaseAddress,
    'mailing-address': BaseAddress
  }
})
export default class OfficeAddresses extends Mixins(CommonMixin, EntityFilterMixin) {
  /**
   * Indicates whether this component should be enabled or not.
   */
  @Prop({ default: true })
  readonly componentEnabled: boolean

  /**
   * Addresses object from the parent page.
   * If this is null then this is a new filing; otherwise these are the addresses from a draft filing.
   * This will be emitted back to the parent page when the addresses are updated.
   */
  @Prop({ default: null })
  readonly addresses: BcorpAddressIf | null

  /**
   * Registered Office address object passed in from the parent which is pulled from store.
   * This address is used as a baseline address in the event the user wants to reset the changes before submitting.
   */
  @Prop({ default: null })
  private registeredAddress: BaseAddressObjIF

  /**
   * Records Office address object passed in from the parent which is pulled from store.
   * This address is used as a baseline address in the event the user wants to reset the changes before submitting.
   */
  @Prop({ default: null })
  private recordsAddress: BaseAddressObjIF

  // The two addresses that come from the store. These are used to reset the address.
  private deliveryAddressOriginal = {} as AddressIF
  private mailingAddressOriginal = {} as AddressIF

  // The two addresses that come from the store. These are used to reset the address.
  private recDeliveryAddressOriginal = {} as AddressIF
  private recMailingAddressOriginal = {} as AddressIF

  // The two addresses that are the current state of the BaseAddress components.
  private deliveryAddress = {} as AddressIF
  private mailingAddress = {} as AddressIF

  // The two addresses that are the current state of the BaseAddress components.
  private recDeliveryAddress = {} as AddressIF
  private recMailingAddress = {} as AddressIF

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
  private inheritRegisteredAddress: boolean = this.isSame(this.registeredAddress, this.recordsAddress)

  // The Address schema containing Vuelidate rules.
  private addressSchema: {} = officeAddressSchema

  // Entity Enum
  readonly EntityTypes: {} = EntityTypes

  /**
   * Lifecycle callback to initialize the data when the component when it is created.
   */
  private created (): void {
    this.initAddresses()
  }
  /**
   * Lifecycle callback to set up the component when it is mounted.
   */
  private mounted (): void {
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
    let deliveryAddressFinal = {} as AddressIF
    let mailingAddressFinal = {} as AddressIF
    let recDeliveryAddressFinal = {} as AddressIF
    let recMailingAddressFinal = {} as AddressIF

    if (this.registeredAddress) {
      deliveryAddressFinal = { ...this.deliveryAddress }
      mailingAddressFinal = { ...this.mailingAddress }

      // if the address has changed from the original, set action flag
      this.addressModified(this.deliveryAddress, this.registeredAddress.deliveryAddress)
        ? this.addAction(deliveryAddressFinal, ADDRESSCHANGED)
        : this.removeAction(deliveryAddressFinal, ADDRESSCHANGED)

      // if the address has changed from the original, set action flag
      this.addressModified(this.mailingAddress, this.registeredAddress.mailingAddress)
        ? this.addAction(mailingAddressFinal, ADDRESSCHANGED)
        : this.removeAction(mailingAddressFinal, ADDRESSCHANGED)
    }

    if (this.recordsAddress) {
      recDeliveryAddressFinal = { ...this.recDeliveryAddress }
      recMailingAddressFinal = { ...this.recMailingAddress }

      // if the address has changed from the original, set action flag
      this.addressModified(this.recDeliveryAddress, this.recDeliveryAddressOriginal)
        ? this.addAction(recDeliveryAddressFinal, ADDRESSCHANGED)
        : this.removeAction(recDeliveryAddressFinal, ADDRESSCHANGED)

      // if the address has changed from the original, set action flag
      this.addressModified(this.recMailingAddress, this.recMailingAddressOriginal)
        ? this.addAction(recMailingAddressFinal, ADDRESSCHANGED)
        : this.removeAction(recMailingAddressFinal, ADDRESSCHANGED)
    }

    if (this.recordsAddress) {
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
    } else {
      return {
        registeredOffice: {
          deliveryAddress: deliveryAddressFinal,
          mailingAddress: mailingAddressFinal
        }
      }
    }
  }

  /**
   * Called when addresses property changes (ie, when parent page has loaded a draft filing).
   */
  @Watch('addresses')
  onAddressesChanged (): void {
    if (this.addresses && this.addresses.recordsOffice) {
      this.inheritRegisteredAddress =
        this.isSame(this.addresses.registeredOffice.deliveryAddress,
          this.addresses.recordsOffice.deliveryAddress, 'actions') &&
        this.isSame(this.addresses.registeredOffice.mailingAddress,
          this.addresses.recordsOffice.mailingAddress, 'actions')
    }
    this.deliveryAddress = isEmpty(this.addresses)
      ? {} as AddressIF
      : this.addresses.registeredOffice['deliveryAddress']
    this.mailingAddress = isEmpty(this.addresses)
      ? {} as AddressIF
      : this.addresses.registeredOffice['mailingAddress']

    if (this.recordsAddress) {
      this.recDeliveryAddress = isEmpty(this.addresses)
        ? {} as AddressIF
        : this.addresses.recordsOffice['deliveryAddress']

      this.recMailingAddress = isEmpty(this.addresses)
        ? {} as AddressIF
        : this.addresses.recordsOffice['mailingAddress']
    }
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
      this.isSame(this.deliveryAddress, this.deliveryAddressOriginal) &&
      this.isSame(this.mailingAddress, this.mailingAddressOriginal) &&
      this.isSame(this.recDeliveryAddress, this.recDeliveryAddressOriginal) &&
      this.isSame(this.recMailingAddress, this.recMailingAddressOriginal)
    )
  }

  /**
   * Computed value of whether or not the address has been modified from the original.
   *
   * @returns a boolean that is true if the address has been modified, or false otherwise.
   */
  private addressModified (address: AddressIF, addressOriginal: AddressIF): boolean {
    return !this.isSame(address, addressOriginal)
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
  private updateAddressValid (addressToValidate: string, isValid: boolean): void {
    switch (addressToValidate) {
      case 'deliveryAddress':
        this.deliveryAddressValid = isValid
        break
      case 'mailingAddress':
        this.mailingAddressValid = isValid
        break
      case 'recDeliveryAddress':
        this.recDeliveryAddressValid = isValid
        break
      case 'recMailingAddress':
        this.recMailingAddressValid = isValid
        break
      default:
        // eslint-disable-next-line no-console
        console.log(`Error: Address- ${addressToValidate} not found`)
        break
    }
    this.emitValid()
  }

  /**
   * Sets up the component for editing, retaining a copy of current state so that the user can cancel.
   */
  private editAddress (): void {
    // Check for inherited values
    this.inheritDeliveryAddress = this.isSame(this.mailingAddress, this.deliveryAddress)
    this.inheritRecDeliveryAddress = this.isSame(this.recMailingAddress, this.recDeliveryAddress)

    this.showAddressForm = true
  }

  /**
   * Cancels the editing of addresses, setting the addresses to the value they had before editing began.
   */
  private cancelEditAddress (): void {
    this.deliveryAddress = { ...this.deliveryAddressOriginal }
    this.mailingAddress = { ...this.mailingAddressOriginal }
    this.recDeliveryAddress = { ...this.recDeliveryAddressOriginal }
    this.recMailingAddress = { ...this.recMailingAddressOriginal }
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
    this.inheritRegisteredAddress = this.isSame(this.registeredAddress, this.recordsAddress)
    this.emitAddresses()
    this.emitModified()
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
   * Initialize and assign base states of Address Data
   *
   */
  private initAddresses (): void {
    // If loading loading from a draft filing
    if (this.addresses) {
      this.addresses.registeredOffice && this.assignRegisteredAddresses(this.addresses.registeredOffice)
      this.addresses.recordsOffice && this.assignRecordAddresses(this.addresses.recordsOffice)
    } else {
      // If new filing load from addresses from store
      this.registeredAddress && this.assignRegisteredAddresses(this.registeredAddress)
      this.recordsAddress && this.assignRecordAddresses(this.recordsAddress)
    }

    // emit address data back up so that parent data has data (needed for AR filing specifically)
    this.emitAddresses()
  }

  /**
   * Assign the Registered address objects actions and omit the addressType
   *
   * @param addressBase The base address object to be parsed and assigned to its Office Address class property
   */
  private assignRegisteredAddresses (addressBase: BaseAddressObjIF): void {
    // Assign Delivery Address
    const deliveryAddress = addressBase.deliveryAddress
    if (deliveryAddress) {
      deliveryAddress.actions = []
      this.deliveryAddressOriginal = { ...deliveryAddress }
      if (isEmpty(this.deliveryAddress)) {
        this.deliveryAddress = { ...deliveryAddress }
      }
    } else {
      // eslint-disable-next-line no-console
      console.log('invalid Delivery Address =', addressBase)
    }

    // Assign Mailing Address
    const mailingAddress = addressBase.mailingAddress
    if (mailingAddress) {
      mailingAddress.actions = []
      this.mailingAddressOriginal = { ...mailingAddress }
      if (isEmpty(this.mailingAddress)) {
        this.mailingAddress = { ...mailingAddress }
      }
    } else {
      // eslint-disable-next-line no-console
      console.log('invalid Mailing Address =', addressBase)
    }
  }

  /**
   * Assign the Records address objects actions and omit the addressType
   *
   * @param addressBase The base address object to be parsed and assigned to its Office Address class property
   */
  private assignRecordAddresses (addressBase: BaseAddressObjIF): void {
  // Assign Delivery Address
    const deliveryAddress = addressBase.deliveryAddress
    if (deliveryAddress) {
      deliveryAddress.actions = []
      this.recDeliveryAddressOriginal = { ...deliveryAddress }
      if (isEmpty(this.recDeliveryAddress)) {
        this.recDeliveryAddress = { ...deliveryAddress }
      }
    } else {
      // eslint-disable-next-line no-console
      console.log('invalid Delivery Address =', addressBase)
    }

    // Assign Mailing Address
    const mailingAddress = addressBase.mailingAddress
    if (mailingAddress) {
      mailingAddress.actions = []
      this.recMailingAddressOriginal = { ...mailingAddress }
      if (isEmpty(this.recMailingAddress)) {
        this.recMailingAddress = { ...mailingAddress }
      }
    } else {
      // eslint-disable-next-line no-console
      console.log('invalid Mailing Address =', addressBase)
    }
  }
}
</script>

<style lang="scss" scoped>
// @import '../../assets/styles/theme.scss';

.address-list-container {
  padding: 1.25rem;
}

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
      width: 12rem;
    }
  }

  .meta-container__inner {
    flex: 1 1 auto;
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
.address-wrapper {
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
  margin-left: 4.65rem;
  margin-bottom: -1.5rem;
  padding: 0;

  .v-messages {
    display: none!important;
  }
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
    font-size: 1rem;
    font-weight: bold;
    line-height: 1.375rem;
  }
}
</style>
