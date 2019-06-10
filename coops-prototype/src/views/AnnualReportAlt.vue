<template>
  <div>

    <!-- Initial Page Load Transition -->
    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
        <div class="loading-msg">Preparing Your 2019 Annual Report</div>
      </div>
    </div>

    <!-- Transition to Payment -->
    <v-fade-transition>
      <div class="loading-container" v-show="showLoading">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">{{this.loadingMsg}}</div>
        </div>
      </div>
    </v-fade-transition>

    <EntityInfo/>

    <v-container class="view-container">
      <article id="example-content" :class="this.agmDate ? 'agm-date-selected':'no-agm-date-selected'">
        <header>
          <h1>File 2019 Annual Report</h1>
          <p>Select your Annual General Meeting (AGM) date, and verify or change your Registered Office Address and List of Directors as of your Annual General Meeting.</p>
        </header>

        <!-- Annual General Meeting Dates -->
        <section>
          <header>
            <h2 class="mb-3">1. Annual General Meeting Date</h2>
            <v-card flat>
              <ARFilingDates ref="ARFilingDate" v-on:childToParent="onChildClick"/>
            </v-card>
          </header>
        </section>

        <!-- Addresses -->
        <section>
          <header>
            <h2>2. Registered Office Addresses <span class="agm-date">(as of 2019 Annual General Meeting)</span></h2>
            <p>Verify or change your Registered Office Addresses.</p>
          </header>
          <v-card flat>
            <ul class="list address-list" v-bind:class="{ 'show-address-form' : showAddressForm }">
              <li class="container">
                <div class="meta-container">
                  <label>Delivery Address</label>
                  <div class="meta-container__inner">

                    <!-- START: Static Details (Delivery Address) -->
                    <v-expand-transition>
                      <div class="registered-office-address" v-show="!showAddressForm">
                        <div class="address">
                          <div class="address__row">{{DeliveryAddressStreet}}</div>
                          <div class="address__row">
                            <span>{{DeliveryAddressCity}}</span>
                            <span>&nbsp;{{DeliveryAddressRegion}}</span>
                            <span>&nbsp;{{DeliveryAddressPostalCode}}</span>
                          </div>
                          <div class="address__row">{{DeliveryAddressCountry}}</div>
                        </div>
                        <div class="actions">
                          <v-btn small flat color="primary"
                            @click="editAddress">
                            <v-icon small>edit</v-icon>
                            <span>Change</span>
                          </v-btn>
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
                          <v-select box class="item" label="Province"
                            :items="regionList"
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
                        <div class="registered-office-address">
                          <div class="address">
                            <div class="address__row">{{MailingAddressStreet}}</div>
                            <div class="address__row">
                              <span>{{MailingAddressCity}}</span>
                              <span>&nbsp;{{MailingAddressRegion}}</span>
                              <span>&nbsp;{{MailingAddressPostalCode}}</span>
                            </div>
                            <div class="address__row">{{MailingAddressCountry}}</div>
                          </div>
                        </div>
                      </div>
                    <!-- END: Static Details (Mailing Address) -->
                    </v-expand-transition>

                    <!-- START: Form / Editable Fields (Mailing Address) -->
                    <v-expand-transition>
                      <v-form class="form" v-show="showAddressForm" v-model="mailingAddressFormValid" lazy-validation>
                        <div class="form__row">
                          <v-checkbox class="inherit-checkbox" color="primary" label="Same as Delivery Address" v-model="inheritDeliveryAddress"></v-checkbox>
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
                              <v-select class="item" box label="Province"
                                :items="regionList"
                                v-model="MailingAddressRegion"
                                disabled>
                              </v-select>
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
                          <v-btn class="form-primary-btn" color="primary"
                            @click="addAddressFee">
                            Done</v-btn>
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

        <!-- Director Information -->
        <section>
          <header>
            <h2>3. Directors <!-- <span class="agm-date">({{this.agmDate}})</span> --></h2>
            <p>Tell us who was elected or appointed and who ceased to be a director at your 2018 AGM.</p>

            <v-expand-transition>
              <div v-show="!showNewDirectorForm">
                <v-btn class="new-director-btn" outline color="primary"
                  @click="addNewDirector">
                  <v-icon>add</v-icon>
                  <span>Appoint New Director</span>
                </v-btn>
              </div>
            </v-expand-transition>

          </header>

          <v-card flat>

            <!-- New Director Form -->
            <v-expand-transition>
              <ul class="list new-director" v-show="showNewDirectorForm">
                <li class="container">
                  <div class="meta-container">
                    <label class="mb-3">Appoint New Director</label>
                    <p class="section-description">List the full name and residential address of all directors as of the adjournment of the Annual General Meeting. The residential address of a director must be a complete physical address.</p>
                    <div class="meta-container__inner">
                      <v-form ref="newDirectorForm" v-on:submit.prevent="addNewDirector" v-model="directorFormValid" lazy-validation>
                        <div class="form__row alt-form">
                          <section class="column">
                            <h3>Director Name</h3>
                            <v-text-field box class="item" label="First Name"
                              v-model="director.firstName"
                              :rules="directorFirstNameRules"
                              required></v-text-field>
                            <v-text-field box label="Initial" class="item director-initial"
                              v-model="director.initial"
                            ></v-text-field>
                            <v-text-field box class="item" label="Last Name"
                              v-model="director.lastName"
                              :rules="directorLastNameRules"
                              required></v-text-field>
                          </section>
                          <div class="spacer"></div>
                          <section class="column">
                            <h3>Home Address</h3>
                            <v-text-field box label="Street Address"
                              v-model="director.street"
                              :rules="directorStreetRules"
                              required>
                            </v-text-field>
                            <v-text-field class="item" box label="City"
                            v-model="director.city"
                              :rules="directorCityRules"
                              required>
                            </v-text-field>
                            <v-select class="item" box label="Province"
                              :items="regionList"
                              :rules="directorRegionRules"
                              v-model="director.region">
                            </v-select>
                            <v-text-field class="item" box label="Postal Code"
                              v-model="director.postalCode"
                              :rules="directorPostalCodeRules"
                              required>
                            </v-text-field>
                            <v-select box label="Country"
                              :items="countryList"
                              :rules="directorCountryRules"
                              v-model="director.country" >
                            </v-select>
                          </section>
                          <div class="spacer"></div>
                          <section class="column">
                            <h3>Appointed</h3>
                            2018 Annual General Meeting<br> {{this.agmDate}}
                          </section>
                        </div>
                        <div class="form__row form__btns">
                          <v-btn class="form-primary-btn" @click="validateNewDirectorForm" color="primary">Done</v-btn>
                          <v-btn @click="cancelNewDirector">Cancel</v-btn>
                        </div>
                      </v-form>
                    </div>
                  </div>
                </li>
              </ul>
            </v-expand-transition>

            <!-- Current Director List -->
            <ul class="list director-list">
              <li class="container"
                v-bind:class="{ 'remove' : !director.isDirectorActive }"
                v-for="(director, index) in orderBy(directors, 'id', -1)"
                v-bind:key="index">
                <v-expand-transition>
                  <div class="meta-container" v-show="activeIndex !== index">
                    <label>
                      <span>{{director.firstName}}</span><span>&nbsp;{{director.lastName}}</span>
                      <div class="director-status">
                        <v-scale-transition>
                          <v-chip small label disabled color="blue" text-color="white" v-show="director.isNew">
                            New
                          </v-chip>
                        </v-scale-transition>
                        <v-scale-transition>
                          <v-chip small label disabled v-show="!director.isDirectorActive">
                            Ceased
                          </v-chip>
                        </v-scale-transition>
                      </div>
                    </label>
                    <div class="meta-container__inner">
                      <div class="director-info">
                        <div class="address">
                          <div class="address__row">{{director.street}}</div>
                          <div class="address__row">
                            <span>{{director.city}}</span>
                            <span>&nbsp;{{director.region}}</span>
                            <span>&nbsp;{{director.postalCode}}</span>
                          </div>
                          <div class="address__row">{{director.country}}</div>
                        </div>
                        <div class="actions">
                          <v-btn small flat color="primary"
                            v-show="director.isNew"
                            @click="editDirector(index)">
                            <v-icon small>edit</v-icon>
                            <span>Change</span>
                          </v-btn>
                          <v-btn small flat color="primary"
                            v-show="!director.isNew"
                            @click="removeDirector(director)">
                            <v-icon small>{{director.isDirectorActive ? 'close':'undo'}}</v-icon>
                            <span>{{director.isDirectorActive ? 'Cease':'Undo'}}</span>
                          </v-btn>
                        </div>
                      </div>
                    </div>
                  </div>
                </v-expand-transition>
                <v-expand-transition>
                  <div class="meta-container new-director" v-show="activeIndex === index">
                    <label class="mb-3">{{director.firstName}} {{director.lastName}}</label>
                    <div class="meta-container__inner">
                      <v-form ref="editDirectorForm"
                        v-show="activeIndex === index"
                        v-model="directorFormValid" lazy-validation>
                        <div class="form__row alt-form">
                          <section class="column">
                            <h3>Director Name</h3>
                            <v-text-field box class="item" label="First Name"
                              v-model="director.firstName"
                              :rules="directorFirstNameRules"
                              required></v-text-field>
                            <v-text-field box label="Initial" class="item director-initial"
                              v-model="director.initial"
                            ></v-text-field>
                            <v-text-field box class="item" label="Last Name"
                              v-model="director.lastName"
                              :rules="directorLastNameRules"
                              required></v-text-field>
                          </section>
                          <div class="spacer"></div>
                          <section class="column">
                            <h3>Home Address</h3>
                            <v-text-field box label="Street Address"
                              v-model="director.street"
                              :rules="directorStreetRules"
                              required>
                            </v-text-field>
                            <v-text-field class="item" box label="City"
                            v-model="director.city"
                              :rules="directorCityRules"
                              required>
                            </v-text-field>
                            <v-select class="item" box label="Province"
                              :items="regionList"
                              :rules="directorRegionRules"
                              v-model="director.region">
                            </v-select>
                            <v-text-field class="item" box label="Postal Code"
                              v-model="director.postalCode"
                              :rules="directorPostalCodeRules"
                              required>
                            </v-text-field>
                            <v-select box label="Country"
                              :items="countryList"
                              :rules="directorCountryRules"
                              v-model="director.country" >
                            </v-select>
                          </section>
                          <div class="spacer"></div>
                          <section class="column">
                            <h3>Appointed</h3>
                            2018 Annual General Meeting
                          </section>
                        </div>
                        <div class="form__row form__btns">
                          <v-btn class="form-primary-btn" color="primary"
                            @click="cancelEditDirector(index)">
                            Done</v-btn>
                          <v-btn @click="cancelEditDirector(index)">Cancel</v-btn>
                        </div>
                      </v-form>
                    </div>
                  </div>
                </v-expand-transition>
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
    <v-container class="pt-0">
      <div class="ar-filing-buttons">
        <v-btn color="primary" large @click="fileAndPay"> File & Pay</v-btn>
        <v-btn large to="/Dashboard">Cancel</v-btn>
      </div>
    </v-container>
  </div>
</template>

<script lang='ts'>
import { Component, Vue } from 'vue-property-decorator'
import Vue2Filters from 'vue2-filters'
import { Affix } from 'vue-affix'
import ARFilingDates from '@/components/ARFilingDates.vue'
import EntityInfo from '@/components/EntityInfo.vue'
import FeeSummary from '@/components/FeeSummary.vue'
import moment from 'moment'

Vue.use(Vue2Filters)
Vue.prototype.moment = moment

export default {
  name: 'AnnualReportAlt',
  mixins: [Vue2Filters.mixin],
  components: {
    Affix,
    ARFilingDates,
    EntityInfo,
    FeeSummary
  },

  data () {
    return {
      agmDate: '',
      isAgmStepComplete: false,

      countryList: [
        'Canada'
      ],
      regionList: [
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
      activeIndex: undefined,
      isEditingDirector: false,
      isDirectorActive: true,
      director: { id:"", firstName: "", lastName: "", street: "", city: "", region: "", postalCode: "", country: "" },
      directors: [
        { id: 1, isNew: false, isDirectorActive: true, firstName: "Jon", lastName: "Lee", initial: "", street: "14 Maple Street", city: "Vancouver", region: "BC", postalCode: "V7L 2W9", country: "Canada"},
        { id: 2, isNew: false, isDirectorActive: true, firstName: "Alli", lastName: "Myers", initial: "", street: "1111 First Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"},
        { id: 3, isNew: false, isDirectorActive: true, firstName: "Nora", lastName: "Patton", initial: "", street: "2222 Second Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"},
        { id: 4, isNew: false, isDirectorActive: true, firstName: "Phoebe", lastName: "Jones", initial: "", street: "3333 Third Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"},
        { id: 5, isNew: false, isDirectorActive: true, firstName: "Cole", lastName: "Bryan", initial: "", street: "4444 Fourth Street", city: "Victoria", region: "BC", postalCode: "V8A 2G8", country: "Canada"}
      ],

      //Director Form Validation
      directorFormValid: true,
      directorFirstNameRules: [
        v => !!v || 'A first name is required',
      ],
      directorLastNameRules: [
        v => !!v || 'A last name is required',
      ],
      directorStreetRules: [
        v => !!v || 'A street address is required',
      ],
      directorCityRules: [
        v => !!v || 'A city is required',
      ],
      directorRegionRules: [
        v => !!v || 'A region is required',
      ],
      directorPostalCodeRules: [
        v => !!v || 'A postal code is required',
      ],
      directorCountryRules: [
        v => !!v || 'A country is required',
      ],

      showLoading: false,
      loadingMsg: 'Redirecting to PayBC to Process Your Payment'
    }
  },

  methods: {
    onChildClick (value) {
      this.agmDate = value
    },

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

    cancelNewDirector: function () {
      this.showNewDirectorForm = false
      this.$refs.newDirectorForm.reset()
    },

    deleteDirector: function (director, index) {
      if(this.directors[index] === director) {
        this.directors.splice(index, 1)
        this.activeIndex = null
      } else {
        let found = this.directors.indexOf(director)
        this.directors.splice(found, 1)
        this.activeIndex = null
      }
    },

    validateNewDirectorForm: function (index) {
      if (this.$refs.newDirectorForm.validate()) {
        this.pushNewDirectorData()
        this.cancelNewDirector()
        this.addDirectorFee()
      }
      else {
      }
    },

    pushNewDirectorData: function (index) {
      let newDirector = {
        id: this.directors.length + 1,
        firstName: this.director.firstName,
        initial: this.director.initial,
        lastName: this.director.lastName,
        street: this.director.street,
        city: this.director.city,
        region: this.director.region,
        postalCode: this.director.postalCode,
        country: this.director.country,
        isDirectorActive: true,
        isNew: true
      }
      this.directors.push(newDirector)
    },

    pushEditDirectorData: function (index) {
      let updateDirector = {
        firstName: this.director.firstName,
        initial: this.director.initial,
        lastName: this.director.lastName,
        street: this.director.street,
        city: this.director.city,
        region: this.director.region,
        postalCode: this.director.postalCode,
        country: this.director.country,
      }
      this.directors.push(updateDirector)
    },

    // Remove Director
    removeDirector: function (director) {
      director.isDirectorActive = !director.isDirectorActive
      this.addDirectorFee()
    },

    // Modify Existing Directors
    editDirector: function (index) {
      this.activeIndex = index
      this.cancelNewDirector()
      this.cancelEditAddress()
    },

    closeEditDirector: function (index) {
      this.activeIndex = undefined
    },

    cancelEditDirector: function (index) {
      this.activeIndex = undefined
    },

    // Add Fees
    addAddressFee: function () {
      this.$refs.feeSummary.addChangeAddressFee()
      this.showAddressForm = false
    },

    addDirectorFee: function () {
      this.$refs.feeSummary.addChangeDirectorFee()
    },

    gotoPayment: function () {
      this.$router.push({ path: '/Payment' })
    },

    fileAndPay: function () {
      this.showLoading = true
      setTimeout(() => { this.gotoPayment() }, 2000)
    }
  }
}
</script>

<style lang="stylus" scoped>
@import "../assets/styles/theme.styl"

article
  .v-card
    line-height 1.2rem
    font-size 0.875rem

  .v-btn
    margin 0
    text-transform none

section p
  //font-size 0.875rem
  color $gray6

section + section
  margin-top 3rem

h2
  margin-bottom 0.25rem

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

    .v-btn
      min-width 5rem

    .v-btn + .v-btn
      margin-left 0.5rem

@media (min-width 768px)
  .meta-container
    flex-flow row nowrap

    > label:first-child
      flex 0 0 auto
      padding-right: 2rem
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


// Address Block Layout
.address
  display flex
  flex-direction column

.address__row
  flex 1 1 auto

// Registered Office Address
.registered-address-info
  display flex

  .status
    flex 1 1 auto

  .actions
    flex 0 0 auto

.show-address-form
  li:first-child
    padding-bottom 0

// Director Display
.director-info
  display flex

  .status
    flex 1 1 auto

  .actions
    flex 0 0 auto

.director-initial
  max-width 6rem

.new-director-btn
  margin-bottom 1.5rem !important

  .v-icon
    margin-left -0.5rem

// Filing Buttons
.ar-filing-buttons
  padding-top 2rem
  border-top: 1px solid $gray5
  text-align right
  .v-btn + .v-btn
    margin-left 0.5rem

// V-chip customization
.v-chip--small
  height 1.2rem !important
  margin 0
  margin-top 0.5rem
  padding 0
  text-transform uppercase
  font-size 0.65rem
  font-weight 700
  vertical-align top

  .v-chip__content
    height 1.2rem !important
    padding 0 0.5rem

.remove
  color $gray5 !important

.agm-date
  margin-left 0.25rem
  font-weight 300

.new-director .meta-container,
.meta-container.new-director
  flex-flow column nowrap

  > label:first-child
    margin-bottom 1.5rem

  .alt-form
    display flex
    margin-bottom 1rem

    section
      flex 1 1 auto
      margin 0
      width: 33.3333%

      h3
        margin-bottom 1rem
        font-size 0.875rem

.section-description
  font-size 0.875rem
  line-height 1.25rem

.spacer
  margin-right 0.75rem
  margin-left 0.75rem
  border-left 1px solid $gray4

</style>
