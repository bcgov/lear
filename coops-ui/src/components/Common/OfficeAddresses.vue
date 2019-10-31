<template>
  <v-card flat>
    <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">
      <li class="container">
        <div class="meta-container">
          <label>Registered Office</label>
          <div class="meta-container__inner">
            <label>Delivery Address</label>
            <delivery-address
              :address="registeredAddress.deliveryAddress"
              :editing="showAddressForm"
              :schema="addressSchema"
              v-on:update:address="updateDelivery($event)"
              @valid="isDeliveryValid"
            />
            <label>Mailing Address</label>
            <v-checkbox
              class="inherit-checkbox"
              label="Same as Delivery Address"
              v-if="showAddressForm"
              v-model="inheritDeliveryAddress"
            ></v-checkbox>
            <delivery-address
              v-if="!showAddressForm || !inheritDeliveryAddress"
              :address="registeredAddress.mailingAddress"
              :editing="showAddressForm"
              :schema="addressSchema"
              v-on:update:address="updateMailing($event)"
              @valid="isMailingValid"
            />
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

<!--        <div class="meta-container">-->
<!--          <label>Record Office</label>-->
<!--          <div class="meta-container__inner">-->
<!--            <label>Delivery Address</label>-->
<!--            <div class="form__row">-->
<!--              <v-checkbox-->
<!--                class="inherit-checkbox"-->
<!--                label="Same as Delivery Address"-->
<!--                v-if="showAddressForm"-->
<!--                v-model="inheritDeliveryAddress"-->
<!--              ></v-checkbox>-->
<!--            </div>-->
<!--            <delivery-address-->
<!--              v-if="!showAddressForm || !inheritDeliveryAddress"-->
<!--              :address="recordsAddress.deliveryAddress"-->
<!--              :editing="showAddressForm"-->
<!--              :schema="addressSchema"-->
<!--              v-on:update:address="updateMailing($event)"-->
<!--              @valid="isMailingValid"-->
<!--            />-->
<!--            <label>Mailing Address</label>-->
<!--            <mailing-address-->
<!--              :address="recordsAddress.mailingAddress"-->
<!--              :editing="showAddressForm"-->
<!--              :schema="addressSchema"-->
<!--              v-on:update:address="updateDelivery($event)"-->
<!--              @valid="isDeliveryValid"-->
<!--            />-->
<!--          </div>-->
<!--        </div>-->
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
          >Update Addresses</v-btn>
          <v-btn id="reg-off-cancel-addr-btn" @click="cancelEditAddress">Cancel</v-btn>
        </div>
      </li>
    </ul>
  </v-card>
</template>

<script lang="ts">

// Libraries
import axios from '@/axios-auth'
import { mapState } from 'vuex'
import isEmpty from 'lodash.isempty'
import { required, maxLength } from 'vuelidate/lib/validators'
import { Component, Vue, Emit, Prop, Watch, Mixins } from 'vue-property-decorator'

// Components
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'

// Mixins
import { AddressMixin, CommonMixin } from '@/mixins'

// Interfaces
import { BaseAddressObjIF } from '@/interfaces/address-interfaces'

// action constants
const ADDRESSCHANGED = 'addressChanged'

interface AddressObject {
    actions?: string[]
}

@Component({
  components: {
    'delivery-address': BaseAddress,
    'mailing-address': BaseAddress
  }
})
export default class OfficeAddresses extends Mixins(AddressMixin, CommonMixin) {
    /**
     * The identifier for the legal entity that is to have its addresses retrieved from the API.
     */
    @Prop({ default: '' })
    readonly legalEntityNumber: string

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
    readonly addresses: object

    // The two addresses that come from the API. These are used to reset the address.
    private registeredAddressOriginal: {} = {}
    private recordsAddressOriginal: {} = {}

    // The two addresses that are the current state of the BaseAddress components.
    private registeredAddress: {} = {}
    private recordsAddress: {} = {}

    // The two addresses where the above are stored prior to an edit. These allow a cancel to the address prior to
    // edit, which if there was a prior edit will not be the data that originally came from the API.
    private registeredAddressTemp: {} = {}
    private recordsAddressTemp: {} = {}

    // Validation events from BaseAddress.
    private registeredAddressValid: boolean = true
    private recordsAddressValid: boolean = true

    // Whether to show the editable forms for the addresses (true) or just the static display addresses (false).
    private showAddressForm: boolean = false

    // State of the form checkbox for determining whether or not the mailing address is the same as the delivery address
    private inheritDeliveryAddress: boolean = true

    // The Address schema containing Vuelidate rules.
    // NB: This should match the subject JSON schema.
    private addressSchema = {
      streetAddress: {
        required,
        maxLength: maxLength(50)
      },
      streetAddressAdditional: {
        maxLength: maxLength(50)
      },
      addressCity: {
        required,
        maxLength: maxLength(40)
      },
      addressCountry: {
        required
        // isCanada: (val) => (val.toLower() === 'canada') // FUTURE
      },
      addressRegion: {
        required,
        maxLength: maxLength(2)
      },
      postalCode: {
        required,
        maxLength: maxLength(15)
      },
      deliveryInstructions: {
        maxLength: maxLength(80)
      }
    }

    /**
     * Lifecycle callback to set up the component when it is mounted.
     */
    private mounted (): void {
      this.loadAddressesFromApi(this.legalEntityNumber)
      // this.setupCanadaPost()
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
      console.log(this.registeredAddress)
      console.log(this.recordsAddress)

      let registeredAddressFinal = Object.assign({}, this.registeredAddress)
      let recordsAddressFinal = Object.assign({}, this.recordsAddress)

      // if the address has changed from the original, set action flag
      if (this.registeredModified) this.addAction(registeredAddressFinal, ADDRESSCHANGED)
      else this.removeAction(registeredAddressFinal, ADDRESSCHANGED)

      // if the mailing address has changed from the original, set action flag
      if (this.recordModified) this.addAction(recordsAddressFinal, ADDRESSCHANGED)
      else this.removeAction(recordsAddressFinal, ADDRESSCHANGED)

      return { registeredAddress: registeredAddressFinal, recordsAddress: recordsAddressFinal }
    }

    /**
     * Called when addresses property changes (ie, when parent page has loaded a draft filing).
     */
    @Watch('addresses')
    onAddressesChanged (): void {
      this.registeredAddress = isEmpty(this.addresses) ? {} : this.addresses['registeredOffice']
      this.recordsAddress = isEmpty(this.addresses) ? {} : this.addresses['recordsOffice']
    }

    /**
     * Computed value of whether or not the address form is valid.
     *
     * @returns a boolean that is true if the data on the form is valid, or false otherwise.
     */
    private get formValid (): boolean {
      return this.registeredAddressValid && (this.inheritDeliveryAddress || this.recordsAddressValid)
    }

    /**
     * Computed value of whether or not an address has been modified from the original.
     *
     * @returns a boolean that is true if one or both addresses have been modified, or false otherwise.
     */
    private get modified (): boolean {
      // Unfortunately we cannot use the modified event from the BaseAddress components due to timing issues on loading
      // since we're using the API to load on mount. That should be looked into at some point.
      return !(
        this.isSameAddress(this.registeredAddress, this.registeredAddressOriginal) &&
          this.isSameAddress(this.recordsAddress, this.recordsAddressOriginal))
    }

    /**
     * Computed value of whether or not the mailing address has been modified from the original.
     *
     * @returns a boolean that is true if the mailing address has been modified, or false otherwise.
     */
    private get recordModified (): boolean {
      return !this.isSameAddress(this.recordsAddress, this.recordsAddressOriginal)
    }

    /**
     * Computed value of whether or not the delivery address has been modified from the original.
     *
     * @returns a boolean that is true if the delivery address has been modified, or false otherwise.
     */
    private get registeredModified (): boolean {
      return !this.isSameAddress(this.registeredAddress, this.registeredAddressOriginal)
    }

    /**
     * Event callback to update the delivery address when its component changes.
     *
     * @param address the object containing the new address.
     */
    private updateDelivery (address: object): void {
      // Note that we do a copy of the fields (rather than change the object reference) to prevent an infinite loop with
      // the property.
      Object.assign(this.registeredAddress, address)
    }

    /**
     * Event callback to keep track of the validity of the delivery address.
     *
     * @param valid a boolean indicating the validity of the address.
     */
    private isDeliveryValid (valid: boolean): void {
      this.registeredAddressValid = valid
      this.emitValid()
    }

    /**
     * Event callback to update the mailing address when its component changes.
     *
     * @param address the object containing the new address.
     */
    private updateMailing (address: object): void {
      // Note that we do a copy of the fields (rather than change the object reference) to prevent an infinite loop with
      // the property.
      Object.assign(this.recordsAddress, address)
    }

    /**
     * Event callback to keep track of the validity of the mailing address.
     *
     * @param valid a boolean indicating the validity of the address.
     */
    private isMailingValid (valid: boolean): void {
      this.recordsAddressValid = valid
      this.emitValid()
    }

    /**
     * Sets up the component for editing, retaining a copy of current state so that the user can cancel.
     */
    private editAddress (): void {
      this.inheritDeliveryAddress = this.isSameAddress(this.recordsAddress, this.registeredAddress)
      this.registeredAddressTemp = { ...this.registeredAddress }
      this.recordsAddressTemp = { ...this.recordsAddress }

      this.showAddressForm = true
    }

    /**
     * Cancels the editing of addresses, setting the addresses to the value they had before editing began.
     */
    private cancelEditAddress (): void {
      this.registeredAddress = { ...this.registeredAddressTemp }
      this.recordsAddress = { ...this.recordsAddressTemp }

      this.showAddressForm = false
    }

    /**
     * Updates the address data using what was entered on the forms.
     */
    private updateAddress (): void {
      if (this.inheritDeliveryAddress) {
        this.recordsAddress = { ...this.registeredAddress }
      }
      this.showAddressForm = false
      this.emitAddresses()
      this.emitModified()
    }

    /**
     * Resets the address data to what it was before any edits were done.
     */
    private resetAddress (): void {
      this.registeredAddress = { ...this.registeredAddressOriginal }
      this.recordsAddress = { ...this.recordsAddressOriginal }
      this.emitAddresses()
      this.emitModified()
    }

    /**
     * Loads the office addresses from an API call.
     *
     * @param legalEntityNumber the identifier for the legal entity whose office addresses are fetched.
     */
    private loadAddressesFromApi (legalEntityNumber: string): void {
      if (legalEntityNumber) {
        const url = legalEntityNumber + '/addresses'
        axios.get(url)
          .then(response => {
            if (response && response.data) {
              const registeredAddress = response.data.registeredOffice
              if (registeredAddress) {
                registeredAddress.actions = []

                // this.registeredAddressOriginal = { ...this.omitProp(registeredAddress, ['deliveryAddress.addressType']) }
                this.registeredAddressOriginal = registeredAddress

                // If parent page loaded draft before this API call, don't overwrite draft delivery address.
                // Otherwise this API call finished before parent page loaded draft, or parent page won't
                // load draft (ie, this is a new filing) -> initialize delivery address.
                if (isEmpty(this.registeredAddress)) {
                  // this.registeredAddress = { ...this.omitProp(registeredAddress.deliveryAddress, ['addressType']) }
                  this.registeredAddress = registeredAddress
                }
              } else {
                console.log('loadAddressesFromApi() error - invalid Delivery Address =', registeredAddress)
              }

              const recordAddress = response.data.recordsOffice
              if (recordAddress) {
                recordAddress.actions = []
                console.log(recordAddress)
                // this.registeredAddressOriginal = { ...this.omitProp(registeredAddress, ['deliveryAddress.addressType']) }
                this.recordsAddressOriginal = recordAddress

                // If parent page loaded draft before this API call, don't overwrite draft delivery address.
                // Otherwise this API call finished before parent page loaded draft, or parent page won't
                // load draft (ie, this is a new filing) -> initialize delivery address.
                if (isEmpty(this.recordsAddress)) {
                  // this.registeredAddress = { ...this.omitProp(registeredAddress.deliveryAddress, ['addressType']) }
                  this.recordsAddress = recordAddress
                }
              } else {
                console.log('loadAddressesFromApi() error - invalid Delivery Address =', registeredAddress)
              }

              // emit address data back up so that parent data has data (needed for AR filing specifically)
              // this.emitAddresses()
            } else {
              console.log('loadAddressesFromApi() error - invalid response =', response)
            }
          })
          .catch(error => console.error('loadAddressesFromApi() error =', error))
      }
    }

    /**
     * Sets up the Canada Post address completion fields.
     */
    /*
    private setupCanadaPost (): void {
      if (deliveryCanadaPostObject) {
        deliveryCanadaPostObject.listen('populate', autoCompleteResponse => {
          this.deliveryAddress['streetAddress'] = autoCompleteResponse.Line1
          this.deliveryAddress['streetAddressAdditional'] = autoCompleteResponse.Line2
          this.deliveryAddress['addressCity'] = autoCompleteResponse.City
          this.deliveryAddress['addressRegion'] = autoCompleteResponse.ProvinceCode
          this.deliveryAddress['postalCode'] = autoCompleteResponse.PostalCode
          this.deliveryAddress['addressCountry'] = autoCompleteResponse.CountryName
        })
        deliveryCanadaPostObject.listen('country', autoCompleteResponse => {
          this.deliveryAddress['addressCountry'] = autoCompleteResponse.name
        })
      }

      if (mailingCanadaPostObject) {
        mailingCanadaPostObject.listen('populate', autoCompleteResponse => {
          this.mailingAddress['streetAddress'] = autoCompleteResponse.Line1
          this.mailingAddress['streetAddressAdditional'] = autoCompleteResponse.Line2
          this.mailingAddress['addressCity'] = autoCompleteResponse.City
          this.mailingAddress['addressRegion'] = autoCompleteResponse.ProvinceCode
          this.mailingAddress['postalCode'] = autoCompleteResponse.PostalCode
          this.mailingAddress['addressCountry'] = autoCompleteResponse.CountryName
        })
        mailingCanadaPostObject.listen('country', autoCompleteResponse => {
          this.mailingAddress['addressCountry'] = autoCompleteResponse.name
        })
      }
    }
    */

    /**
     * Add an action, if it doesn't already exist; ensures no multiples.
     */
    private addAction (address: AddressObject, val: string): void {
      if (address.actions.indexOf(val) < 0) address.actions.push(val)
    }

    /**
     * Remove an action, if it already exists.
     */
    private removeAction (address: AddressObject, val: string): void {
      address.actions = address.actions.filter(el => el !== val)
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
      margin-top: 0;
    }
  }
  // List Layout
  .list {
    li {
      border-bottom: 1px solid $gray3;
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
