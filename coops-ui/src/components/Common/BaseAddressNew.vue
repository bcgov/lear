//
// Copyright © 2019 Province of British Columbia
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
// the License. You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//

<template>
  <div class="meta-container__inner">
    <!-- Display fields -->
    <v-expand-transition>
      <div class="address-block"
           v-show="!editing"
      >
        <div class="address-block__info">
          <div class="address-block__info-row">
            {{ addressLocal.streetAddress }}
          </div>
          <div class="address-block__info-row">
            {{ addressLocal.streetAddressAdditional }}
          </div>
          <div class="address-block__info-row">
            <span>{{ addressLocal.addressCity }}</span>
            <span v-if="addressLocal.addressRegion !== '--'">&nbsp;{{ addressLocal.addressRegion }}</span>
            <span v-if="addressLocal.postalCode !== 'N/A'">&nbsp;&nbsp;{{ addressLocal.postalCode }}</span>
          </div>
          <div class="address-block__info-row">
            {{ addressLocal.addressCountry }}
          </div>
          <div class="address-block__info-row"
               v-if="addressLocal.deliveryInstructions"
          >
            {{ addressLocal.deliveryInstructions }}
          </div>
        </div>
      </div>
    </v-expand-transition>

    <!-- Edit fields -->
    <v-expand-transition>
      <v-form lazy-validation
              name="address-form"
              ref="addressForm"
              v-show="editing"
      >
        <div class="form__row">
          <v-text-field autocomplete="address-complete"
                        filled
                        label="Street Address"
                        name="street-address"
                        v-model="addressLocal.streetAddress"
                        :rules="streetRules"
                        @click="enableAddressComplete"
          ></v-text-field>
        </div>
        <div class="form__row">
          <v-text-field filled
                        label="Additional Street Address (Optional)"
                        name="street-address-additional"
                        v-model="addressLocal.streetAddressAdditional"
          ></v-text-field>
        </div>
        <div class="form__row three-column">
          <v-text-field filled
                        class="item"
                        label="City"
                        name="address-city"
                        required
                        v-model="addressLocal.addressCity"
                        :rules="cityRules"
          ></v-text-field>
          <v-select filled
                    class="item"
                    label="Province"
                    name="address-region"
                    v-model="addressLocal.addressRegion"
                    :items="regions"
                    :rules="regionRules"
          ></v-select>
          <v-text-field filled
                        class="item"
                        label="Postal Code"
                        name="postal-code"
                        required
                        v-model="addressLocal.postalCode"
                        :rules="postalCodeRules"
          ></v-text-field>
        </div>
        <div class="form__row">
          <v-text-field filled
                        label="Country"
                        name="address-country"
                        required
                        v-model="addressLocal.addressCountry"
                        :rules="countryRules"
          ></v-text-field>
        </div>
        <div class="form__row">
          <v-textarea auto-grow
                      filled
                      label="Delivery Instructions (Optional)"
                      name="delivery-instructions"
                      rows="2"
                      v-model="addressLocal.deliveryInstructions"
          />
        </div>
      </v-form>
    </v-expand-transition>
  </div>
</template>

<script lang="ts">

import Vue from 'vue'
import { Component, Emit, Prop, Watch } from 'vue-property-decorator'
import { validationMixin } from 'vuelidate'
import { required } from 'vuelidate/lib/validators'

    /**
     * The component for displaying and editing an address.
     */
    @Component({
      mixins: [validationMixin],
      validations: {
        address: {
          streetAddress: {
            required
          },
          addressCity: {
            required
          },
          addressRegion: {
            required
          },
          postalCode: {
            required
          },
          addressCountry: {
            required
          }
        }
      }
    })
export default class BaseAddressNew extends Vue {
        /**
         * Contains the address (if any) to be edited.
         */
        @Prop({ default: () => {} }) readonly address: object

        /**
         * Indicates whether the address should be shown in editing mode (true) or display mode (false).
         */
        @Prop({ default: false }) readonly editing: boolean

        /**
         * A local copy of the address object, to contain the fields edited by the component.
         */
        private addressLocal: object = { ...this.address }

        /**
         * A copy of the address that the component was originally created with. This is used to determine whether or not the
         * address has been edited by the user.
         */
        private addressOriginal: object = { ...this.address }

        /**
         * Has this component been mounted yet? Initially unset, but will be set by the {@link mounted} lifecycle callback.
         */
        private isMounted: boolean

        /**
         * The provinces for the address region drop-down list.
         */
        private readonly regions: string[] = [
          'BC', 'AB', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT', '--'
        ]

        // TODO: Convert from Vuetify validation to Vuelidate using JSON Schema - temporarily using Vuetify for display.
        private readonly streetRules = [ v => !!v || 'A street address is required' ]
        private readonly cityRules = [ v => !!v || 'A city is required' ]
        private readonly regionRules = [ v => !!v || 'A province is required' ]
        private readonly postalCodeRules = [ v => !!v || 'A postal code is required' ]
        private readonly countryRules = [ v => !!v || 'A country is required' ]

        /**
         * Lifecycle callback to convert the address JSON into an object, so that it can be used by the template.
         */
        private created (): void {
          // Let the parent know right away about the validity of the address.
          this.emitValid()
        }

        /**
         * Lifecycle callback to store the mounted state of the component. We don't want the address watcher firing events
         * while the component is being set up.
         */
        private mounted (): void {
          this.isMounted = true
        }

        /**
         * Emits an update message for the {@link address} property, so that the caller can ".sync" with it.
         *
         * @returns the {@link addressLocal} object.
         */
        @Emit('update:address')
        private emitAddress (): object {
          return this.addressLocal
        }

        /**
         * Emits the validity state of the address entered by the user.
         *
         * @returns a boolean that is true if the address if valid, false otherwise.
         */
        @Emit('valid')
        private emitValid (): boolean {
          return !this.$v.$invalid
        }

        /**
         * Emits the modified state of the address.
         *
         * @returns a boolean that is true if the address has been modified, false otherwise.
         */
        @Emit('modified')
        private emitModified (): boolean {
          return BaseAddressNew.stringify(this.addressOriginal) !== BaseAddressNew.stringify(this.addressLocal)
        }

        /**
         * Watches changes to the address object, so that if the parent changes the data, then the object copy of it that
         * backs the display will be updated.
         */
        @Watch('address', { deep: true })
        private onAddressChanged (): void {
          this.addressLocal = { ...this.address }
        }

        /**
         * Watches changes to the addressLocal object, to catch any changes to the fields within the address. Will notify the
         * parent object with the new address and whether or not the address is valid.
         */
        @Watch('addressLocal', { deep: true, immediate: true })
        private onAddressLocalChanged (): void {
          if (this.isMounted) {
            this.emitAddress()
            this.emitValid()
            this.emitModified()
          }
        }

        /**
         * A convenience method for JSON.stringify that strips values that have empty strings.
         *
         * @param object the object to stringify.
         *
         * @returns a string that is the JSON representation of the object.
         */
        private static stringify (object: object): string {
          return JSON.stringify(object, (name: string, val: any) : any => { return val !== '' ? val : undefined })
        }

        /**
         * Enables AddressComplete for this instance of the address.
         */
        private enableAddressComplete (): void {
          // If you want to use this component with the Canada Post AddressComplete service, it needs the following:
          //  1. The AddressComplete JavaScript script include must be done to set up "window.pca".
          //  2. Your AddressComplete account key must be defined as "window.addressCompleteKey".
          const pca = window['pca']
          const key = window['addressCompleteKey']
          if (!pca || !key) {
            return
          }

          // Sets the id for the two form elements that are used by the AddressComplete code. If necessary this removes the
          // id from previous elements.
          this.moveElementId('street-address')
          this.moveElementId('address-country')

          // Destroy the old one if it exists, and create the new.

          if (window['currentAddressComplete']) {
            window['currentAddressComplete'].destroy()
          }

          window['currentAddressComplete'] = this.createAddressComplete(pca, key)
        }

        /**
         * Sets the id attribute of the named element to the name. If there was a pre-existing element with the id already
         * set, it will be unset.
         *
         * @param name the name of the element for which to set the id.
         */
        private moveElementId (name: string): void {
          const oldElement = document.getElementById(name)
          const thisElement = this.$el.querySelector('[name="' + name + '"]')

          // If it's already set, don't do it again.
          if (oldElement !== thisElement) {
            if (oldElement) {
              oldElement.id = ''
            }

            thisElement.id = name
          }
        }

        /**
         * Creates the AddressComplete object for this instance of the component.
         *
         * @param pca the Postal Code Anywhere object provided by AddressComplete.
         * @param key the key for the Canada Post account that is to be charged for lookups.
         *
         * @return an object that is a pca.Address instance.
         */
        private createAddressComplete (pca, key: string): object {
          // Set up the two fields that AddressComplete will use for input.
          const addressFields = [
            { element: 'street-address', mode: pca.fieldMode.SEARCH },
            { element: 'address-country', mode: pca.fieldMode.COUNTRY }
          ]

          const options = {
            key: key
          }

          const addressComplete = new pca.Address(addressFields, options)

          // The documentation contains sample load/populate callback code that doesn't work, but this will. The side effect
          // is that it breaks the autofill functionality provided by the library, but we really don't want the library
          // altering the DOM because Vue is already doing so, and the two don't play well together.
          addressComplete.listen('populate', this.addressCompletePopulate)

          return addressComplete
        }

        /**
         * Updates the address data after the user chooses a suggested address.
         *
         * @param address the data object returned by the AddressComplete Retrieve API.
         */
        private addressCompletePopulate (address: object): void {
          this.addressLocal['streetAddress'] = address['Line1']
          this.addressLocal['streetAddressAdditional'] = address['Line2']
          this.addressLocal['addressCity'] = address['City']
          this.addressLocal['addressCountry'] = address['CountryIso2']

          if (address['CountryIso2'] === 'CA') {
            this.addressLocal['addressRegion'] = address['ProvinceCode']
            this.addressLocal['postalCode'] = address['PostalCode']
          } else {
            // Not proud of this, but it'll do until we implement JSON Schema validation.
            this.addressLocal['addressRegion'] = '--'
            this.addressLocal['postalCode'] = address['PostalCode'] ? address['PostalCode'] : 'N/A'
          }
        }
}

</script>

<style scoped lang="scss">

  @import '../../assets/styles/theme.scss';

  .meta-container{
    display: flex;
    flex-flow: column nowrap;
    position: relative;
  }

  .validationError{
    border-color: red;
    border-radius: .3rem;
    border-style: groove;
    border-width: thin;
  }

  .validationErrorInfo{
    color: red;
  }

  @media (min-width: 768px){
    .meta-container{
      flex-flow: row nowrap
    }
  }

  // Address Block Layout
  .address-block{
    display: flex;
  }

  .address-block__info{
    flex: 1 1 auto;
  }

  // Form Row Elements
  .form__row.three-column{
    align-items: stretch;
    display: flex;
    flex-flow: row nowrap;
    margin-left: -0.5rem;
    margin-right: -0.5rem;

    .item{
      flex: 1 1 auto;
      flex-basis: 0;
      margin-left: 0.5rem;
      margin-right: 0.5rem;
    }
  }

</style>
