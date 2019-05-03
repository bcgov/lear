<template>
  <div>
    <EntityInfo/>
    <v-container class="view-container">
      <article id="example-content">
        <header>
          <h1>File Annual Report</h1>
          <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.</p>
        </header>

        <!-- Addresses -->
        <section>
          <header>
            <h2>Registered Office Addresses</h2>
            <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium</p>
          </header>
          <v-card>
            <ul class="address-list" v-bind:class="{ 'is-editing' : isEditing}">
              <li>
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
                      <v-form ref="deliveryAddressForm" v-show="showAddressForm" v-model="deliveryAddressFormValid" lazy-validation>
                        <div class="form__row">
                          <v-text-field box label="Street Address"
                            v-model="DeliveryAddressStreet"
                            :rules="DeliveryAddressStreetRules"
                            required>
                            </v-text-field>
                        </div>
                        <div class="form__row three-column">
                          <v-text-field class="item" box label="City"
                            v-model="DeliveryAddressCity"
                            :rules="DeliveryAddressCityRules"
                            required>
                          </v-text-field>
                          <v-select class="item" box label="Province" :items="Regions" v-model="DeliveryAddressRegion" disabled></v-select>
                          <v-text-field class="item" box label="Postal Code"
                            v-model="DeliveryAddressPostalCode"
                            :rules="DeliveryAddressPostalCodeRules"
                            required>
                          </v-text-field>
                        </div>
                        <div class="form__row">
                          <v-text-field box label="Country" v-model="DeliveryAddressCountry" disabled></v-text-field>
                        </div>
                        <div class="form__row">
                          <v-textarea box label="Special Delivery Instructions (Optional)" v-model="DeliveryAddressInstructions"
                          ></v-textarea>
                        </div>
                      </v-form>
                    </v-expand-transition>
                    <!-- END: Form / Editable Fields (Delivery Address) -->

                  </div>
                </div>
              </li>
              <li>
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
                          <v-checkbox class="inherit-checkbox" label="Same as Delivery Address" v-model="inheritDeliveryAddress"></v-checkbox>
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
                              <v-select class="item" box label="Province" :items="Regions" v-model="MailingAddressRegion" disabled></v-select>
                              <v-text-field class="item" box label="Postal Code"
                                v-model="MailingAddressPostalCode"
                                :rules="MailingAddressPostalCodeRules"
                                required>
                              </v-text-field>
                            </div>
                            <div class="form__row">
                              <v-text-field box label="Country" v-model="MailingAddressCountry" disabled></v-text-field>
                            </div>
                            <div class="form__row">
                              <v-textarea box label="Special Delivery Instructions (Optional)" v-model="MailingAddressInstructions"
                              ></v-textarea>
                            </div>
                          </div>
                        </v-expand-transition>
                        <div class="form__row form__btns">
                          <v-btn class="update-btn" color="primary" v-bind:disabled="isAddressChanged"
                            @click="addAddressFee">
                            Update Addresses</v-btn>
                          <v-btn @click="cancelEditAddress">Cancel</v-btn>
                        </div>
                      </v-form>
                    </v-expand-transition>
                    <!-- END: Form / Editable Fields (Mailing Address) -->

                  </div>
                </div>
              </li>
            </ul>
          </v-card>
        </section>

      </article>

      <aside>
        <affix relative-element-selector="#example-content" :offset="{ top: 120, bottom: 40 }">
          <FeeSummary ref="feeSummary"/>
        </affix>
      </aside>

    </v-container>
  </div>
</template>

<script lang='ts'>
import { Component, Vue } from 'vue-property-decorator'
import { Affix } from 'vue-affix'
import EntityInfo from '@/components/EntityInfo.vue'
import FeeSummary from '@/components/FeeSummary.vue'

export default {
  name: 'AnnualReport',
  components: {
    Affix,
    EntityInfo,
    FeeSummary
  },

  data () {
    return {
      isEditing: false,
      isAddressChanged: false,
      showAddressForm: false,
      inheritDeliveryAddress: true,
      deliveryAddressFormValid: true,
      mailingAddressFormValid: true,
      DeliveryAddressStreet: '1234 Main Street',
      DeliveryAddressStreetRules: [
        v => !!v || 'A street address is required',
      ],
      DeliveryAddressCity: 'Victoria',
      DeliveryAddressCityRules: [
        v => !!v || 'A city is required',
      ],
      DeliveryAddressRegion: 'BC',
      DeliveryAddressPostalCode: 'V9A 2G8',
      DeliveryAddressPostalCodeRules: [
        v => !!v || 'A postal code is required',
      ],
      DeliveryAddressCountry: 'Canada',
      DeliveryAddressInstructions: ' ',
      MailingAddressStreet: '4321 Main Street',
      MailingAddressStreetRules: [
        v => !!v || 'A street address is required',
      ],
      MailingAddressCity: 'Victoria',
      MailingAddressCityRules: [
        v => !!v || 'A city is required',
      ],
      MailingAddressRegion: 'BC',
      MailingAddressPostalCode: 'V9A 2G8',
      MailingAddressPostalCodeRules: [
        v => !!v || 'A postal code is required',
      ],
      MailingAddressCountry: 'Canada',
      MailingAddressInstructions: ' ',
      Regions: [
        'BC'
      ]
    }
  },

  methods: {
    editAddress: function () {
      this.isEditing = true
      this.showAddressForm = true
    },
    editMailingAddress: function () {
      this.showMailingAddressForm = true
    },
    cancelEditAddress: function () {
      this.isEditing = false
      this.showAddressForm = false
    },
    addAddressFee: function () {
      this.$refs.feeSummary.addChangeAddressFee()
      this.isAddressChanged = true
    }
  }
}
</script>

<style lang="stylus">
@import "../assets/styles/theme.styl"

// Page Layout
.view-container
  display flex
  flex-flow column nowrap
  padding-top 3rem
  padding-bottom 3rem

  article
    flex 1 1 auto

    section
      margin-top 3rem

  aside
    flex 0 0 auto
    width 20rem
    margin-top 3rem

    .affix
      width 20rem

  section
    > p
      color $gray6
      font-size 0.875rem

@media (max-width 768px)
  .view-container
    aside
      width 100%

      .affix
        position relative
        top 0 !important
        width 100%

@media (min-width 960px)
  .view-container
    flex-flow row nowrap

    article
      margin-right 2rem

    aside
      margin-top 0
      width 20rem

article
  .v-card
    line-height 1.2rem
    font-size 0.875rem

  .v-btn
    margin 0
    min-width 4rem
    text-transform none

// Page Contents
h1
  margin-bottom 1.25rem
  line-height 2rem
  letter-spacing -0.01rem
  font-size 2rem
  font-weight 500

h2
  margin-bottom 0.25rem
  font-size 1.125rem
  font-weight 500

h4
  margin-top 0.5rem
  margin-bottom 1.5rem
  font-size 1.125rem
  font-weight 500

p
  margin-bottom 1rem
  color $gray7

ul
  margin 0
  padding 0
  list-style-type none

.meta-container
  display flex
  flex-flow column nowrap
  position relative

  > label:first-child
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

    > label:first-child
      flex 0 0 auto
      padding-right: 4rem
      width 12rem

// List Layout
.address-list
  padding 1.25rem

  li + li
    padding-top 1.25rem

.address-list.is-editing
  li + li
    padding-top 0

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
  margin-top 0.5rem

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
  margin-top -4px
  margin-left -4px
  padding 0

</style>
