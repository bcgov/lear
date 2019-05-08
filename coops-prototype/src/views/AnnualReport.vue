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
            <h2>1. Registered Office Addresses</h2>
            <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium</p>
          </header>
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
                      <v-form ref="deliveryAddressForm" v-show="showAddressForm" v-model="deliveryAddressFormValid" lazy-validation>
                        <div class="form__row">
                          <v-text-field box label="Street Address"
                            v-model="DeliveryAddressStreet"
                            :rules="DeliveryAddressStreetRules"
                            required>
                            </v-text-field>
                        </div>
                        <div class="form__row three-column">
                          <v-text-field box class="item" label="City"
                            v-model="DeliveryAddressCity"
                            :rules="DeliveryAddressCityRules"
                            required>
                          </v-text-field>
                          <v-select box class="item" label="Province" :items="Regions" v-model="DeliveryAddressRegion" disabled></v-select>
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
                          <v-textarea box rows="2" auto-grow label="Delivery Instructions (Optional)" v-model="DeliveryAddressInstructions"
                          ></v-textarea>
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
                              <v-textarea box rows="2" label="Delivery Instructions (Optional)" v-model="MailingAddressInstructions"
                              ></v-textarea>
                            </div>
                          </div>
                        </v-expand-transition>
                        <div class="form__row form__btns">
                          <v-btn class="update-btn" color="primary"
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

        <section>
          <header>
            <h2>2. Director Information (as of April 1, 2019)</h2>
            <p>Tell us who was elected or appointed and who ceased to be a director at your 2018 AGM.</p>
            <v-expand-transition>
              <div v-show="!showNewDirectorForm">
                <v-btn @click="addNewDirector" outline color="blue" style="margin-bottom: 1.5rem">Add New Director</v-btn>
              </div>
            </v-expand-transition>
          </header>
          <v-card>
            <v-expand-transition>
              <ul class="list director-list" v-show="showNewDirectorForm">
                <li class="container">
                  <div class="meta-container">
                    <label>Add New Director</label>
                    <div class="meta-container__inner">
                      <v-form ref="newDirectorForm" v-on:submit.prevent="addNewDirector" v-model="newDirectorFormValid" lazy-validation>
                        <div class="form__row three-column">
                          <v-text-field box class="item" label="First Name"
                            v-model="director.firstName"
                            :rules="newDirectorFirstNameRules"
                            required></v-text-field>
                          <v-text-field box label="Initial" class="item director-initial"
                            v-model="director.initial"
                          ></v-text-field>
                          <v-text-field box class="item" label="Last Name"
                            v-model="director.lastName"
                            :rules="newDirectorLastNameRules"
                            required></v-text-field>
                        </div>
                        <div class="form__row">
                          <v-text-field box label="Street Address">
                          </v-text-field>
                        </div>
                        <div class="form__row three-column">
                          <v-text-field class="item" box label="City">
                          </v-text-field>
                          <v-select class="item" box label="Province" :items="Regions" disabled></v-select>
                          <v-text-field class="item" box label="Postal Code">
                          </v-text-field>
                        </div>
                        <div class="form__row">
                          <v-text-field box label="Country" disabled></v-text-field>
                        </div>
                        <div class="form__row">
                          <v-textarea box rows="2" auto-grow label="Delivery Instructions (Optional)"
                          ></v-textarea>
                        </div>
                        <div class="form__row form__btns">
                          <v-btn @click="validateNewDirectorForm" color="primary">Add New Director</v-btn>
                          <v-btn @click="cancelNewDirector">Cancel</v-btn>
                        </div>
                      </v-form>
                    </div>
                  </div>
                </li>
              </ul>
            </v-expand-transition>
            <ul class="list director-list">
              <li class="container"
                v-for="(director, index) in orderBy(directors, 'id', -1)"
                v-bind:key="index">
                <div class="meta-container">
                  <label><span>{{director.firstName}}</span><span>&nbsp;{{director.lastName}} {{ director.id }}</span></label>
                  <div class="meta-container__inner">
                    <v-expand-transition>
                      <div class="address-block" v-show="activeIndex !== index">
                        <div class="address-block__info">
                          <div class="address-block__info-row">{{director.street}}</div>
                          <div class="address-block__info-row">
                            <span>{{director.city}}</span>
                            <span>&nbsp;{{director.region}}</span>
                            <span>&nbsp;{{director.postalCode}}</span>
                          </div>
                          <div class="address-block__info-row">{{director.country}}</div>
                        </div>
                        <div class="address-block__actions">
                          <v-btn small outline color="blue" @click="editDirector(index)">Change</v-btn>
                        </div>
                      </div>
                    </v-expand-transition>
                    <v-expand-transition>
                      <v-form ref="directorForm" v-show="activeIndex === index" v-model="directorFormValid" lazy-validation>
                        <div class="form__row three-column">
                          <v-text-field box label="First Name" class="item"
                            v-model="director.firstName"
                            required
                          ></v-text-field>
                          <v-text-field box label="Initial" class="item director-initial"
                            v-model="director.initial"
                          ></v-text-field>
                          <v-text-field box label="Last Name" class="item"
                            v-model="director.lastName"
                          ></v-text-field>
                        </div>
                        <div class="form__row">
                          <v-text-field box label="Street Address"
                            v-model="director.street"
                            required>
                            </v-text-field>
                        </div>
                        <div class="form__row three-column">
                          <v-text-field class="item" box label="City"
                            v-model="director.city"
                            required>
                          </v-text-field>
                          <v-select class="item" box label="Province" :items="Regions" v-model="director.region" disabled></v-select>
                          <v-text-field class="item" box label="Postal Code"
                            v-model="director.postalCode"
                            required>
                          </v-text-field>
                        </div>
                        <div class="form__row">
                          <v-text-field box label="Country" v-model="director.country" disabled></v-text-field>
                        </div>
                        <div class="form__row">
                          <v-textarea box rows="2" auto-grow label="Delivery Instructions (Optional)" v-model="DeliveryAddressInstructions"
                          ></v-textarea>
                        </div>
                        <div class="form__row form__btns">
                          <v-btn class="update-btn" color="primary"
                            @click="addDirectorFee">
                            Update Director</v-btn>
                          <v-btn @click="cancelEditDirector(index)">Cancel</v-btn>
                        </div>
                      </v-form>
                    </v-expand-transition>
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
import Vue2Filters from 'vue2-filters'
import { Affix } from 'vue-affix'
import EntityInfo from '@/components/EntityInfo.vue'
import FeeSummary from '@/components/FeeSummary.vue'

Vue.use(Vue2Filters)

export default {
  name: 'AnnualReport',
  mixins: [Vue2Filters.mixin],
  components: {
    Affix,
    EntityInfo,
    FeeSummary
  },

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

      // Directors
      isEditingDirector: false,
      directorFormValid: false,
      director: { id:"", firstName: "", lastName: "" },
      directors: [
        { id: 1, firstName: "Alli", lastName: "Myers", initial: "", street: "1111 First Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"},
        { id: 2, firstName: "Nora", lastName: "Patton", initial: "", street: "2222 Second Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"},
        { id: 3, firstName: "Phoebe", lastName: "Jones", initial: "", street: "3333 Third Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"},
        { id: 4, firstName: "Cole", lastName: "Bryan", initial: "", street: "4444 Fourth Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"}
      ],
      activeIndex: undefined,

      // New Director Form Validation
      newDirectorFormValid: true,
      newDirectorFirstNameRules: [
        v => !!v || 'A first name is required',
      ],
      newDirectorLastNameRules: [
        v => !!v || 'A last name is required',
      ]
    }
  },

  methods: {
    editAddress: function () {
      this.showAddressForm = true
      this.cancelEditDirector()
    },
    editMailingAddress: function () {
      this.showMailingAddressForm = true
    },
    cancelEditAddress: function () {
      this.showAddressForm = false
    },


    // Add New Director
    addNewDirector: function () {
      this.showNewDirectorForm = true
      this.activeIndex = null
    },
    validateNewDirectorForm: function (index) {
      if (this.$refs.newDirectorForm.validate()) {
        this.pushNewDirectorData()
      }
      else {
      }
    },
    pushNewDirectorData: function (index) {
      let newDirector = {
        id: this.directors.length + 1,
        firstName: this.director.firstName,
        initial: this.director.initial,
        lastName: this.director.lastName
      }
      this.directors.push(newDirector)
    },
    cancelNewDirector: function () {
      this.showNewDirectorForm = false
    },

    // Modify Existing Directors
    editDirector: function (index) {
      this.activeIndex = index
      this.cancelNewDirector()
      this.cancelEditAddress()
    },

    cancelEditDirector: function (index) {
      this.activeIndex = undefined
    },

    // Add Fees
    addAddressFee: function () {
      this.$refs.feeSummary.addChangeAddressFee()
    },
    addDirectorFee: function () {
      this.$refs.feeSummary.addChangeDirectorFee()
    },
  },

  created () {
    let count = 0;

    this.directors.forEach(el => {
      el.id = count;
      count++;
    });

    console.log(this.directors);
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
    header p
      color $gray6
      font-size 1rem

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

// Director Form Fields
.director-initial
  max-width 8rem

</style>
