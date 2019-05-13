<template>
  <div id="registered-office-address">
    <v-container>
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
                      <br/>
                      <v-btn v-if="regOffAddrChange" class="reset-btn" small outline color="red" @click="resetAddress">Reset</v-btn>
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
                        id="street-address"
                        label="Street Address"
                        v-model="DeliveryAddressStreet"
                        :rules="DeliveryAddressStreetRules"
                        required>
                      </v-text-field>
                    </div>
                    <div class="form__row three-column">
                      <v-text-field class="item"
                                    box
                                    id="city"
                                    label="City"
                                    v-model="DeliveryAddressCity"
                                    :rules="DeliveryAddressCityRules"
                                    required>
                      </v-text-field>
                      <v-text-field class="item"
                                box
                                id="state"
                                label="Province"
                                v-model="DeliveryAddressRegion"
                                :rules="DeliveryAddressRegionRules"
                                required>
                      </v-text-field>
                      <v-text-field box
                                    class="item"
                                    id="postcode"
                                    label="Postal Code"
                                    v-model="DeliveryAddressPostalCode"
                                    :rules="DeliveryAddressPostalCodeRules"
                                    required>
                      </v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box
                                    id="country"
                                    label="Country"
                                    v-model="DeliveryAddressCountry"
                                    :rules="DeliveryAddressCountryRules"
                                    required>
                      </v-text-field>
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
        'BC', 'AB', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
      ],

      isEditing: false,
      showAddressForm: false,
      showNewDirectorForm: false,
      inheritDeliveryAddress: true,

      // Validation
      deliveryAddressFormValid: true,
      mailingAddressFormValid: true,

      DeliveryAddressStreet: '',
      tmpDeliveryAddressStreet: '',
      DeliveryAddressStreetRules: [
        v => !!v || 'A street address is required'
      ],
      DeliveryAddressCity: '',
      tmpDeliveryAddressCity: '',
      DeliveryAddressCityRules: [
        v => !!v || 'A city is required'
      ],
      DeliveryAddressRegion: '',
      tmpDeliveryAddressRegion: '',
      DeliveryAddressRegionRules: [
        v => !!v || 'A province/state is required'
      ],
      DeliveryAddressPostalCode: '',
      tmpDeliveryAddressPostalCode: '',
      DeliveryAddressPostalCodeRules: [
        v => !!v || 'A postal code is required'
      ],
      DeliveryAddressCountry: '',
      tmpDeliveryAddressCountry: '',
      DeliveryAddressCountryRules: [
        v => !!v || 'A country is required'
      ],
      DeliveryAddressInstructions: ' ',
      tmpDeliveryAddressInstructions: ' ',
      MailingAddressStreet: '',
      tmpMailingAddressStreet: '',
      MailingAddressStreetRules: [
        v => !!v || 'A street address is required'
      ],
      MailingAddressCity: '',
      tmpMailingAddressCity: '',
      MailingAddressCityRules: [
        v => !!v || 'A city is required'
      ],
      MailingAddressRegion: '',
      tmpMailingAddressRegion: '',
      MailingAddressPostalCode: '',
      tmpMailingAddressPostalCode: '',
      MailingAddressPostalCodeRules: [
        v => !!v || 'A postal code is required'
      ],
      MailingAddressCountry: '',
      tmpMailingAddressCountry: '',
      MailingAddressInstructions: ' ',
      tmpMailingAddressInstructions: ' ',

      activeIndex: undefined
    }
  },

  computed: {
    regOffAddrChange () {
      return this.$store.state.regOffAddrChange
    },
    storeDeliveryAddressStreet () {
      if (this.$store.state.DeliveryAddressStreet == null) return ''
      return this.$store.state.DeliveryAddressStreet
    },
    storeDeliveryAddressCity () {
      if (this.$store.state.DeliveryAddressCity == null) return ''
      return this.$store.state.DeliveryAddressCity
    },
    storeDeliveryAddressRegion () {
      if (this.$store.state.DeliveryAddressRegion == null) return 'Not Available'
      return this.$store.state.DeliveryAddressRegion
    },
    storeDeliveryAddressPostalCode () {
      if (this.$store.state.DeliveryAddressPostalCode == null) return 'Not Available'
      return this.$store.state.DeliveryAddressPostalCode
    },
    storeDeliveryAddressCountry () {
      if (this.$store.state.DeliveryAddressCountry == null) return ''
      return this.$store.state.DeliveryAddressCountry
    },
    storeDeliveryAddressInstructions () {
      if (this.$store.state.DeliveryAddressInstructions == null) return ''
      return this.$store.state.DeliveryAddressInstructions
    },
    storeMailingAddressStreet () {
      if (this.$store.state.MailingAddressStreet == null) return 'Not Available'
      return this.$store.state.MailingAddressStreet
    },
    storeMailingAddressCity () {
      if (this.$store.state.MailingAddressCity == null) return 'Not Available'
      return this.$store.state.MailingAddressCity
    },
    storeMailingAddressRegion () {
      if (this.$store.state.MailingAddressRegion == null) return 'Not Available'
      return this.$store.state.MailingAddressRegion
    },
    storeMailingAddressPostalCode () {
      if (this.$store.state.MailingAddressPostalCode == null) return 'Not Available'
      return this.$store.state.MailingAddressPostalCode
    },
    storeMailingAddressCountry () {
      if (this.$store.state.MailingAddressCountry == null) return ''
      return this.$store.state.MailingAddressCountry
    },
    storeMailingAddressInstructions () {
      if (this.$store.state.MailingAddressInstructions == null) return ''
      return this.$store.state.MailingAddressInstructions
    }
  },
  mounted () {
  },
  methods: {
    editAddress () {
      this.tmpDeliveryAddressStreet = this.DeliveryAddressStreet
      this.tmpDeliveryAddressCity = this.DeliveryAddressCity
      this.tmpDeliveryAddressRegion = this.DeliveryAddressRegion
      this.tmpDeliveryAddressCountry = this.DeliveryAddressCountry
      this.tmpDeliveryAddressPostalCode = this.DeliveryAddressPostalCode
      this.tmpDeliveryAddressInstructions = this.DeliveryAddressInstructions

      this.tmpMailingAddressStreet = this.MailingAddressStreet
      this.tmpMailingAddressCity = this.MailingAddressCity
      this.tmpMailingAddressRegion = this.MailingAddressRegion
      this.tmpMailingAddressCountry = this.MailingAddressCountry
      this.tmpMailingAddressPostalCode = this.MailingAddressPostalCode
      this.tmpMailingAddressInstructions = this.MailingAddressInstructions

      this.showAddressForm = true
    },
    editMailingAddress () {
      this.showMailingAddressForm = true
    },
    cancelEditAddress () {
      this.DeliveryAddressStreet = this.tmpDeliveryAddressStreet
      this.DeliveryAddressCity = this.tmpDeliveryAddressCity
      this.DeliveryAddressRegion = this.tmpDeliveryAddressRegion
      this.DeliveryAddressCountry = this.tmpDeliveryAddressCountry
      this.DeliveryAddressPostalCode = this.tmpDeliveryAddressPostalCode
      this.DeliveryAddressInstructions = this.tmpDeliveryAddressInstructions

      this.MailingAddressStreet = this.tmpMailingAddressStreet
      this.MailingAddressCity = this.tmpMailingAddressCity
      this.MailingAddressRegion = this.tmpMailingAddressRegion
      this.MailingAddressCountry = this.tmpMailingAddressCountry
      this.MailingAddressPostalCode = this.tmpMailingAddressPostalCode
      this.MailingAddressInstructions = this.tmpMailingAddressInstructions

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
      this.checkAddrChange()
      this.$store.state.regOffAddrChange = true
    },
    checkAddrChange () {
      if (this.DeliveryAddressStreet !== this.storeDeliveryAddressStreet ||
        this.DeliveryAddressCity !== this.storeDeliveryAddressCity ||
        this.DeliveryAddressRegion !== this.storeDeliveryAddressRegion ||
        this.DeliveryAddressCountry !== this.storeDeliveryAddressCountry ||
        this.DeliveryAddressPostalCode !== this.storeDeliveryAddressPostalCode ||
        this.DeliveryAddressInstructions !== this.storeDeliveryAddressInstructions ||
        this.MailingAddressStreet !== this.storeMailingAddressStreet ||
        this.MailingAddressCity !== this.storeMailingAddressCity ||
        this.MailingAddressRegion !== this.storeMailingAddressRegion ||
        this.MailingAddressCountry !== this.storeMailingAddressCountry ||
        this.MailingAddressPostalCode !== this.storeMailingAddressPostalCode ||
        this.MailingAddressInstructions !== this.storeMailingAddressInstructions) {
        this.$store.state.regOffAddrChange = true
      } else {
        this.$store.state.regOffAddrChange = false
      }
    },
    resetAddress () {
      this.$store.state.regOffAddrChange = false

      this.DeliveryAddressStreet = this.storeDeliveryAddressStreet
      this.DeliveryAddressCity = this.storeDeliveryAddressCity
      this.DeliveryAddressRegion = this.storeDeliveryAddressRegion
      this.DeliveryAddressCountry = this.storeDeliveryAddressCountry
      this.DeliveryAddressPostalCode = this.storeDeliveryAddressPostalCode
      this.DeliveryAddressInstructions = this.storeDeliveryAddressInstructions

      this.MailingAddressStreet = this.storeMailingAddressStreet
      this.MailingAddressCity = this.storeMailingAddressCity
      this.MailingAddressRegion = this.storeMailingAddressRegion
      this.MailingAddressCountry = this.storeMailingAddressCountry
      this.MailingAddressPostalCode = this.storeMailingAddressPostalCode
      this.MailingAddressInstructions = this.storeMailingAddressInstructions
    }
  },
  watch: {
    storeDeliveryAddressStreet: function (val) {
      console.log('watcher: ', val)
      this.DeliveryAddressStreet = val
    },
    storeDeliveryAddressCity: function (val) {
      this.DeliveryAddressCity = val
    },
    storeDeliveryAddressRegion: function (val) {
      this.DeliveryAddressRegion = val
    },
    storeDeliveryAddressPostalCode: function (val) {
      this.DeliveryAddressPostalCode = val
    },
    storeDeliveryAddressCountry: function (val) {
      this.DeliveryAddressCountry = val
    },
    storeDeliveryAddressInstructions: function (val) {
      this.DeliveryAddressInstructions = val
    },
    storeMailingAddressStreet: function (val) {
      this.MailingAddressStreet = val
    },
    storeMailingAddressCity: function (val) {
      this.DeliveryAddressCity = val
    },
    storeMailingAddressRegion: function (val) {
      this.MailingAddressCity = val
    },
    storeMailingAddressPostalCode: function (val) {
      this.MailingAddressPostalCode = val
    },
    storeMailingAddressCountry: function (val) {
      this.MailingAddressCountry = val
    },
    storeMailingAddressInstructions: function (val) {
      this.MailingAddressInstructions = val
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
    min-width 6rem
    text-transform none

  .reset-btn
    margin-top .5rem

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
