<template>
  <div id="registered-office-address">
    <v-container class="view-container">
      <v-card>
        <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">
          <li class="container">
            <div class="meta-container">
              <label>Delivery Address</label>
              <div class="meta-container__inner">

                <!-- START: Static Details (Delivery Address) -->
                <v-expand-transition>
                  <div class="address-block" v-show="!showAddressForm">
                    <div class="address-block__info">
                      <div class="address-block__info-row">{{DeliveryAddressStreet}}</div>
                      <div class="address-block__info-row">
                        <span>{{DeliveryAddressCity}}</span>
                        <span>&nbsp;{{DeliveryAddressRegion}}</span>
                        <span>&nbsp;{{DeliveryAddressPostalCode}}</span>
                      </div>
                      <div class="address-block__info-row">{{DeliveryAddressCountry}}</div>
                    </div>
                    <div class="address-block__actions">
                      <v-btn small outline color="blue" @click="editAddress">Change</v-btn>
                    </div>
                  </div>
                </v-expand-transition>
                <!-- END: Static Details (Delivery Address) -->

                <!-- START: Form / Editable Fields (Delivery Address) -->
                <v-expand-transition>
                  <v-form ref="deliveryAddressForm"
                          v-show="showAddressForm"
                          v-model="deliveryAddressFormValid"
                          lazy-validation>
                    <div class="form__row">
                      <v-text-field
                        box
                        label="Street Address"
                        v-model="DeliveryAddressStreet"
                        :rules="DeliveryAddressStreetRules"
                        required>
                      </v-text-field>
                    </div>
                    <div class="form__row three-column">
                      <v-text-field class="item"
                                    box
                                    label="City"
                                    v-model="DeliveryAddressCity"
                                    :rules="DeliveryAddressCityRules"
                                    required>
                      </v-text-field>
                      <v-select class="item"
                                box
                                label="Province"
                                :items="Regions"
                                v-model="DeliveryAddressRegion"
                                disabled>
                      </v-select>
                      <v-text-field box class="item" label="Postal Code"
                        v-model="DeliveryAddressPostalCode"
                        :rules="DeliveryAddressPostalCodeRules"
                        required>
                      </v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Country" v-model="DeliveryAddressCountry" disabled></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-textarea
                        box
                        rows="2"
                        auto-grow
                        label="Delivery Instructions (Optional)"
                        v-model="DeliveryAddressInstructions">
                      </v-textarea>
                    </div>
                  </v-form>
                </v-expand-transition>
                <!-- END: Form / Editable Fields (Delivery Address) -->

              </div>
            </div>
          </li>
          <li class="container">
            <div class="meta-container">
              <label>Mailing Address</label>
              <div class="meta-container__inner">

                <!-- START: Static Details (Mailing Address) -->
                <v-expand-transition>
                  <div class="meta-container__inner" v-show="!showAddressForm">
                    <div class="address-block">
                      <div class="address-block__info">
                        <div class="address-block__info-row">{{MailingAddressStreet}}</div>
                        <div class="address-block__info-row">
                          <span>{{MailingAddressCity}}</span>
                          <span>&nbsp;{{MailingAddressRegion}}</span>
                          <span>&nbsp;{{MailingAddressPostalCode}}</span>
                        </div>
                        <div class="address-block__row">{{MailingAddressCountry}}</div>
                      </div>
                    </div>
                  </div>
                <!-- END: Static Details (Mailing Address) -->
                </v-expand-transition>

                <!-- START: Form / Editable Fields (Mailing Address) -->
                <v-expand-transition>
                  <v-form class="form" v-show="showAddressForm" v-model="mailingAddressFormValid" lazy-validation>
                    <div class="form__row">
                      <v-checkbox class="inherit-checkbox"
                                  label="Same as Delivery Address"
                                  v-model="inheritDeliveryAddress">
                      </v-checkbox>
                    </div>
                    <v-expand-transition>
                      <div v-show="!inheritDeliveryAddress">
                        <div class="form__row">
                          <v-text-field box label="Street Address"
                            v-model="MailingAddressStreet"
                            :rules="MailingAddressStreetRules"
                            required>
                            </v-text-field>
                        </div>
                        <div class="form__row three-column">
                          <v-text-field class="item" box label="City"
                            v-model="MailingAddressCity"
                            :rules="MailingAddressCityRules"
                            required>
                          </v-text-field>
                          <v-select class="item"
                                    box
                                    label="Province"
                                    :items="Regions"
                                    v-model="MailingAddressRegion"
                                    disabled>
                          </v-select>
                          <v-text-field class="item"
                                        box
                                        label="Postal Code"
                                        v-model="MailingAddressPostalCode"
                                        :rules="MailingAddressPostalCodeRules"
                                        required>
                          </v-text-field>
                        </div>
                        <div class="form__row">
                          <v-text-field
                            box label="Country"
                            v-model="MailingAddressCountry"
                            disabled>
                          </v-text-field>
                        </div>
                        <div class="form__row">
                          <v-textarea
                            box rows="2"
                            label="Delivery Instructions (Optional)"
                            v-model="MailingAddressInstructions">
                          </v-textarea>
                        </div>
                      </div>
                    </v-expand-transition>
                    <div class="form__row form__btns">
                      <v-btn class="update-btn"
                             color="primary"
                             :disabled="!deliveryAddressFormValid ||
                              (!mailingAddressFormValid && !inheritDeliveryAddress)"
                             @click="updateAddress">
                        Update Addresses
                      </v-btn>
                      <v-btn @click="cancelEditAddress">
                        Cancel
                      </v-btn>
                    </div>
                  </v-form>
                </v-expand-transition>
                <!-- END: Form / Editable Fields (Mailing Address) -->

              </div>
            </div>
          </li>
        </ul>
      </v-card>
    </v-container>
  </div>
</template>

<script>
export default {
  name: 'RegisteredOfficeAddress.vue',
  data () {
    return {
      Regions: [
        'BC'
      ],

      isEditing: false,
      showAddressForm: false,
      showNewDirectorForm: false,
      inheritDeliveryAddress: true,

      // Validation
      deliveryAddressFormValid: true,
      mailingAddressFormValid: true,
      DeliveryAddressStreet: '1234 Main Street',
      DeliveryAddressStreetRules: [
        v => !!v || 'A street address is required'
      ],
      DeliveryAddressCity: 'Victoria',
      DeliveryAddressCityRules: [
        v => !!v || 'A city is required'
      ],
      DeliveryAddressRegion: 'BC',
      DeliveryAddressPostalCode: 'V9A 2G8',
      DeliveryAddressPostalCodeRules: [
        v => !!v || 'A postal code is required'
      ],
      DeliveryAddressCountry: 'Canada',
      DeliveryAddressInstructions: ' ',
      MailingAddressStreet: '4321 Main Street',
      MailingAddressStreetRules: [
        v => !!v || 'A street address is required'
      ],
      MailingAddressCity: 'Victoria',
      MailingAddressCityRules: [
        v => !!v || 'A city is required'
      ],
      MailingAddressRegion: 'BC',
      MailingAddressPostalCode: 'V9A 2G8',
      MailingAddressPostalCodeRules: [
        v => !!v || 'A postal code is required'
      ],
      MailingAddressCountry: 'Canada',
      MailingAddressInstructions: ' ',

      activeIndex: undefined
    }
  },

  methods: {
    editAddress () {
      this.showAddressForm = true
    },
    editMailingAddress () {
      this.showMailingAddressForm = true
    },
    cancelEditAddress () {
      this.showAddressForm = false
    },
    updateAddress () {
      if (this.inheritDeliveryAddress) {
        this.MailingAddressStreet = this.DeliveryAddressStreet
        this.MailingAddressCity = this.DeliveryAddressCity
        this.MailingAddressRegion = this.DeliveryAddressRegion
        this.MailingAddressCountry = this.DeliveryAddressCountry
        this.MailingAddressPostalCode = this.DeliveryAddressPostalCode
        this.MailingAddressInstructions = this.DeliveryAddressInstructions
      }
      this.showAddressForm = false
    }
  }
}
</script>

<style scoped lang="stylus">
@import "../../assets/styles/theme.styl"

  .v-card
    line-height 1.2rem
    font-size 0.875rem

  .v-btn
    margin 0
    min-width 4rem
    text-transform none

  .meta-container
    display flex
    flex-flow column nowrap
    position relative

  .meta-container__inner
    margin-top 1rem

  label:first-child
    font-weight 500

  &__inner
    flex 1 1 auto

  .actions
    position absolute
    top 0
    right 0

  @media (min-width 768px)
    .meta-container
      flex-flow row nowrap

      label:first-child
        flex 0 0 auto
        padding-right: 4rem
        width 12rem
    .meta-container__inner
      margin-top 0

  // List Layout
  .list
    li
      border-bottom 1px solid $gray3

  .address-list .form
    margin-top 1rem

  @media (min-width 768px)
    .address-list .form
      margin-top 0

  // Address Block Layout
  .address-block
    display flex

  .address-block__info
    flex 1 1 auto

  .address-block__actions
    position absolute
    top 0
    right 0

  // Form Row Elements
  .form__row + .form__row
    margin-top 0.25rem

  .form__btns
    text-align right

    .v-btn
      margin 0

      + .v-btn
        margin-left 0.5rem

  .form__row.three-column
    display flex
    flex-flow row nowrap
    align-items stretch
    margin-right -0.5rem
    margin-left -0.5rem

    .item
      flex 1 1 auto
      flex-basis 0
      margin-right 0.5rem
      margin-left 0.5rem

  .inherit-checkbox
    margin-top -3px
    margin-left -3px
    padding 0

  // Registered Office Address Form Behavior
  .show-address-form
    li:first-child
      padding-bottom 0

  ul
    margin 0
    padding 0
    list-style-type none
</style>
