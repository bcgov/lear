<template>
  <div id="registered-office-address">

    <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">
      <li class="container">
        <div class="meta-container">
          <label>Delivery Address</label>
          <div class="meta-container__inner">

            <!-- START: Static Details (Delivery Address) -->
            <v-expand-transition>
              <div id="delivery-address-display" class="address-block" v-show="!showAddressForm">
                <div class="address-block__info">
                  <div class="address-block__info-row">{{DeliveryAddressStreet}}</div>
                  <div class="address-block__info-row" v-if="DeliveryAddressStreetAdditional">
                    {{DeliveryAddressStreetAdditional}}
                  </div>
                  <div class="address-block__info-row">
                    <span>{{DeliveryAddressCity}}</span>
                    <span>&nbsp;{{DeliveryAddressRegion}}</span>
                    <span>&nbsp;{{DeliveryAddressPostalCode}}</span>
                  </div>
                  <div class="address-block__info-row">{{DeliveryAddressCountry}}</div>
                </div>
                <div class="address-block__actions">
                  <v-btn id="reg-off-addr-change-btn"
                          small flat color="primary" :disabled="!agmEntered" @click="editAddress">
                    <v-icon small>edit</v-icon>
                    <span>Change</span>
                  </v-btn>
                  <br/>
                  <v-btn id="reg-off-addr-reset-btn"
                          v-if="regOffAddrChange" class="reset-btn" small outline color="red" @click="resetAddress">
                    Reset
                  </v-btn>
                </div>
              </div>
            </v-expand-transition>
            <!-- END: Static Details (Delivery Address) -->

            <!-- START: Form / Editable Fields (Delivery Address) -->
            <v-expand-transition>
              <v-form id="delivery-address-form"
                      ref="deliveryAddressForm"
                      v-show="showAddressForm"
                      v-model="deliveryAddressFormValid"
                      lazy-validation>
                <div class="form__row">
                  <v-text-field
                    box
                    id="delivery-street-address"
                    label="Street Address Line 1"
                    v-model="DeliveryAddressStreet"
                    :rules="DeliveryAddressStreetRules"
                    maxlength="50"
                    required>
                  </v-text-field>
                </div>
                <div class="form__row">
                  <v-text-field
                    box
                    id="delivery-street-address-additional"
                    label="Street Address Line 2"
                    v-model="DeliveryAddressStreetAdditional"
                    maxlength="50">
                  </v-text-field>
                </div>
                <div class="form__row three-column">
                  <v-text-field class="item"
                                box
                                id="delivery-city"
                                label="City"
                                v-model="DeliveryAddressCity"
                                :rules="DeliveryAddressCityRules"
                                maxlength="15"
                                required>
                  </v-text-field>
                  <v-select class="item"
                            box
                            id="delivery-state"
                            label="Province"
                            :items="Regions"
                            v-model="DeliveryAddressRegion"
                            required>
                  </v-select>
                  <v-text-field box
                                class="item"
                                id="delivery-postcode"
                                label="Postal Code"
                                v-model="DeliveryAddressPostalCode"
                                :rules="DeliveryAddressPostalCodeRules"
                                maxlength="10"
                                required>
                  </v-text-field>
                </div>
                <div class="form__row">
                  <v-text-field box
                                id="delivery-country"
                                label="Country"
                                v-model="DeliveryAddressCountry"
                                :rules="DeliveryAddressCountryRules"
                                maxlength="15"
                                required>
                  </v-text-field>
                </div>
                <div class="form__row">
                  <v-textarea
                    box
                    rows="2"
                    auto-grow
                    label="Delivery Instructions (Optional)"
                    v-model="DeliveryAddressInstructions"
                    maxlength="80">
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
              <div id="mailing-address-display" class="meta-container__inner" v-show="!showAddressForm">
                <div class="address-block">
                  <div class="address-block__info">
                    <div class="address-block__info-row">{{MailingAddressStreet}}</div>
                    <div class="address-block__info-row" v-if="MailingAddressStreetAdditional">
                      {{MailingAddressStreetAdditional}}
                    </div>
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
              <v-form id="mailing-address-form"
                      class="form"
                      v-show="showAddressForm"
                      v-model="mailingAddressFormValid"
                      lazy-validation>
                <div class="form__row">
                  <v-checkbox class="inherit-checkbox"
                              label="Same as Delivery Address"
                              v-model="inheritDeliveryAddress">
                  </v-checkbox>
                </div>
                <v-expand-transition>
                  <div id="mailing-address-expanded" v-show="!inheritDeliveryAddress">
                    <div class="form__row">
                      <v-text-field
                        box
                        label="Street Address Line 1"
                        id="mailing-street-address"
                        v-model="MailingAddressStreet"
                        :rules="MailingAddressStreetRules"
                        maxlength="50"
                        required>
                        </v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field
                        box
                        label="Street Address Line 2"
                        id="mailing-street-address-additional"
                        v-model="MailingAddressStreetAdditional"
                        maxlength="50">
                        </v-text-field>
                    </div>
                    <div class="form__row three-column">
                      <v-text-field
                        class="item"
                        box
                        id="mailing-city"
                        label="City"
                        v-model="MailingAddressCity"
                        :rules="MailingAddressCityRules"
                        maxlength="15"
                        required>
                      </v-text-field>
                      <v-select class="item"
                                box
                                id="mailing-state"
                                label="Province"
                                :items="Regions"
                                v-model="MailingAddressRegion"
                                required>
                      </v-select>
                      <v-text-field class="item"
                                    box
                                    id="mailing-postcode"
                                    label="Postal Code"
                                    v-model="MailingAddressPostalCode"
                                    :rules="MailingAddressPostalCodeRules"
                                    maxlength="10"
                                    required>
                      </v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field
                        box
                        id="mailing-country"
                        label="Country"
                        v-model="MailingAddressCountry"
                        maxlength="15"
                        required>
                      </v-text-field>
                    </div>
                    <div class="form__row">
                      <v-textarea
                        box rows="2"
                        label="Delivery Instructions (Optional)"
                        v-model="MailingAddressInstructions"
                        maxlength="80">
                      </v-textarea>
                    </div>
                  </div>
                </v-expand-transition>
                <div class="form__row form__btns">
                  <v-btn id="reg-off-update-addr-btn"
                          class="update-btn"
                          color="primary"
                          :disabled="!deliveryAddressFormValid ||
                          (!mailingAddressFormValid && !inheritDeliveryAddress)"
                          @click="updateAddress">
                    Update Addresses
                  </v-btn>
                  <v-btn id="reg-off-cancel-addr-btn" @click="cancelEditAddress">
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

      showAddressForm: false,
      inheritDeliveryAddress: true,

      // Validation
      deliveryAddressFormValid: true,
      mailingAddressFormValid: true,

      DeliveryAddressStreet: '',
      tmpDeliveryAddressStreet: '',
      DeliveryAddressStreetRules: [
        v => (v && !!v.trim()) || 'A street address is required'
      ],
      DeliveryAddressStreetAdditional: '',
      tmpDeliveryAddressStreetAdditional: '',
      DeliveryAddressCity: '',
      tmpDeliveryAddressCity: '',
      DeliveryAddressCityRules: [
        v => (v && !!v.trim()) || 'A city is required'
      ],
      DeliveryAddressRegion: '',
      tmpDeliveryAddressRegion: '',
      DeliveryAddressRegionRules: [
        v => (v && !!v.trim()) || 'A province/state is required'
      ],
      DeliveryAddressPostalCode: '',
      tmpDeliveryAddressPostalCode: '',
      DeliveryAddressPostalCodeRules: [
        v => (v && !!v.trim()) || 'A postal code is required'
      ],
      DeliveryAddressCountry: '',
      tmpDeliveryAddressCountry: '',
      DeliveryAddressCountryRules: [
        v => (v && !!v.trim()) || 'A country is required'
      ],
      DeliveryAddressInstructions: '',
      tmpDeliveryAddressInstructions: '',
      MailingAddressStreet: '',
      tmpMailingAddressStreet: '',
      MailingAddressStreetRules: [
        v => (v && !!v.trim()) || 'A street address is required'
      ],
      MailingAddressStreetAdditional: '',
      tmpMailingAddressStreetAdditional: '',
      MailingAddressCity: '',
      tmpMailingAddressCity: '',
      MailingAddressCityRules: [
        v => (v && !!v.trim()) || 'A city is required'
      ],
      MailingAddressRegion: '',
      tmpMailingAddressRegion: '',
      MailingAddressPostalCode: '',
      tmpMailingAddressPostalCode: '',
      MailingAddressPostalCodeRules: [
        v => (v && !!v.trim()) || 'A postal code is required'
      ],
      MailingAddressCountry: '',
      tmpMailingAddressCountry: '',
      MailingAddressInstructions: '',
      tmpMailingAddressInstructions: '',

      activeIndex: undefined
    }
  },

  computed: {
    agmEntered () {
      if (this.$store.state.agmDate) return true
      else if (this.$store.state.noAGM) return true
      else return false
    },
    regOffAddrChange () {
      return this.$store.state.regOffAddrChange
    },
    storeDeliveryAddressStreet () {
      if (this.$store.state.DeliveryAddressStreet == null) return ''
      return this.$store.state.DeliveryAddressStreet
    },
    storeDeliveryAddressStreetAdditional () {
      if (this.$store.state.DeliveryAddressStreetAdditional == null) return ''
      return this.$store.state.DeliveryAddressStreetAdditional
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
      if (this.$store.state.MailingAddressStreet == null) return ''
      return this.$store.state.MailingAddressStreet
    },
    storeMailingAddressStreetAdditional () {
      if (this.$store.state.MailingAddressStreetAdditional == null) return ''
      return this.$store.state.MailingAddressStreetAdditional
    },
    storeMailingAddressCity () {
      if (this.$store.state.MailingAddressCity == null) return ''
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
    var vue = this

    if (deliveryCanadaPostObject) {
      deliveryCanadaPostObject.listen('populate', function (autoCompleteResponse) {
        vue.DeliveryAddressStreet = autoCompleteResponse.Line1
        vue.DeliveryAddressStreetAdditional = autoCompleteResponse.Line2
        vue.DeliveryAddressCity = autoCompleteResponse.City
        vue.DeliveryAddressRegion = autoCompleteResponse.ProvinceCode
        vue.DeliveryAddressPostalCode = autoCompleteResponse.PostalCode
        vue.DeliveryAddressCountry = autoCompleteResponse.CountryName
      })
      deliveryCanadaPostObject.listen('country', function (autoCompleteResponse) {
        vue.DeliveryAddressCountry = autoCompleteResponse.name
      })
    }
    if (mailingCanadaPostObject) {
      mailingCanadaPostObject.listen('populate', function (autoCompleteResponse) {
        vue.MailingAddressStreet = autoCompleteResponse.Line1
        vue.MailingAddressStreetAdditional = autoCompleteResponse.Line2
        vue.MailingAddressCity = autoCompleteResponse.City
        vue.MailingAddressRegion = autoCompleteResponse.ProvinceCode
        vue.MailingAddressPostalCode = autoCompleteResponse.PostalCode
        vue.MailingAddressCountry = autoCompleteResponse.CountryName
      })
      mailingCanadaPostObject.listen('country', function (autoCompleteResponse) {
        vue.MailingAddressCountry = autoCompleteResponse.name
      })
    }
  },
  methods: {
    editAddress () {
      if (this.checkSameAddresses()) this.inheritDeliveryAddress = true
      else this.inheritDeliveryAddress = false

      this.tmpDeliveryAddressStreet = this.DeliveryAddressStreet
      this.tmpDeliveryAddressStreetAdditional = this.DeliveryAddressStreetAdditional
      this.tmpDeliveryAddressCity = this.DeliveryAddressCity
      this.tmpDeliveryAddressRegion = this.DeliveryAddressRegion
      this.tmpDeliveryAddressCountry = this.DeliveryAddressCountry
      this.tmpDeliveryAddressPostalCode = this.DeliveryAddressPostalCode
      this.tmpDeliveryAddressInstructions = this.DeliveryAddressInstructions

      this.tmpMailingAddressStreet = this.MailingAddressStreet
      this.tmpMailingAddressStreetAdditional = this.MailingAddressStreetAdditional
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
      this.DeliveryAddressStreetAdditional = this.tmpDeliveryAddressStreetAdditional
      this.DeliveryAddressCity = this.tmpDeliveryAddressCity
      this.DeliveryAddressRegion = this.tmpDeliveryAddressRegion
      this.DeliveryAddressCountry = this.tmpDeliveryAddressCountry
      this.DeliveryAddressPostalCode = this.tmpDeliveryAddressPostalCode
      this.DeliveryAddressInstructions = this.tmpDeliveryAddressInstructions

      this.MailingAddressStreet = this.tmpMailingAddressStreet
      this.MailingAddressStreetAdditional = this.tmpMailingAddressStreetAdditional
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
        this.MailingAddressStreetAdditional = this.DeliveryAddressStreetAdditional
        this.MailingAddressCity = this.DeliveryAddressCity
        this.MailingAddressRegion = this.DeliveryAddressRegion
        this.MailingAddressCountry = this.DeliveryAddressCountry
        this.MailingAddressPostalCode = this.DeliveryAddressPostalCode
        this.MailingAddressInstructions = this.DeliveryAddressInstructions
      }
      this.showAddressForm = false
      this.checkAddrChange()
    },
    checkSameAddresses () {
      if (this.MailingAddressStreet === this.DeliveryAddressStreet &&
        this.MailingAddressStreetAdditional === this.DeliveryAddressStreetAdditional &&
        this.MailingAddressCity === this.DeliveryAddressCity &&
        this.MailingAddressRegion === this.DeliveryAddressRegion &&
        this.MailingAddressCountry === this.DeliveryAddressCountry &&
        this.MailingAddressPostalCode === this.DeliveryAddressPostalCode &&
        this.MailingAddressInstructions === this.DeliveryAddressInstructions) {
        return true
      }
      return false
    },
    checkAddrChange () {
      if (this.DeliveryAddressStreet !== this.storeDeliveryAddressStreet ||
        this.DeliveryAddressStreetAdditional !== this.storeDeliveryAddressStreetAdditional ||
        this.DeliveryAddressCity !== this.storeDeliveryAddressCity ||
        this.DeliveryAddressRegion !== this.storeDeliveryAddressRegion ||
        this.DeliveryAddressCountry !== this.storeDeliveryAddressCountry ||
        this.DeliveryAddressPostalCode !== this.storeDeliveryAddressPostalCode ||
        this.DeliveryAddressInstructions !== this.storeDeliveryAddressInstructions ||
        this.MailingAddressStreet !== this.storeMailingAddressStreet ||
        this.MailingAddressStreetAdditional !== this.storeMailingAddressStreetAdditional ||
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
      this.DeliveryAddressStreetAdditional = this.storeDeliveryAddressStreetAdditional
      this.DeliveryAddressCity = this.storeDeliveryAddressCity
      this.DeliveryAddressRegion = this.storeDeliveryAddressRegion
      this.DeliveryAddressCountry = this.storeDeliveryAddressCountry
      this.DeliveryAddressPostalCode = this.storeDeliveryAddressPostalCode
      this.DeliveryAddressInstructions = this.storeDeliveryAddressInstructions

      this.MailingAddressStreet = this.storeMailingAddressStreet
      this.MailingAddressStreetAdditional = this.storeMailingAddressStreetAdditional
      this.MailingAddressCity = this.storeMailingAddressCity
      this.MailingAddressRegion = this.storeMailingAddressRegion
      this.MailingAddressCountry = this.storeMailingAddressCountry
      this.MailingAddressPostalCode = this.storeMailingAddressPostalCode
      this.MailingAddressInstructions = this.storeMailingAddressInstructions
    }
  },
  watch: {
    storeDeliveryAddressStreet: function (val) {
      this.DeliveryAddressStreet = val
    },
    storeDeliveryAddressStreetAdditional: function (val) {
      this.DeliveryAddressStreetAdditional = val
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
    storeMailingAddressStreetAdditional: function (val) {
      this.MailingAddressStreetAdditional = val
    },
    storeMailingAddressCity: function (val) {
      this.MailingAddressCity = val
    },
    storeMailingAddressRegion: function (val) {
      this.MailingAddressRegion = val
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

    .v-btn
      min-width 4rem

    .v-btn + .v-btn
      margin-left 0.5rem

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
