<template>
  <div id="directors">

    <v-expand-transition>
      <div v-show="!showNewDirectorForm">
        <v-btn class="new-director-btn" outline color="primary" :disabled="!agmEntered"
          @click="addNewDirector">
          <v-icon>add</v-icon>
          <span>Appoint New Director</span>
        </v-btn>
      </div>
    </v-expand-transition>

    <v-card flat>
      <!-- New Director Form -->
      <v-expand-transition>
        <ul class="list new-director" v-show="showNewDirectorForm">
          <li class="container">
            <div class="meta-container">
              <label>Appoint New Director</label>
              <div class="meta-container__inner">
                <v-form ref="newDirectorForm" v-on:submit.prevent="addNewDirector" v-model="directorFormValid"
                        lazy-validation>
                  <div class="form__row three-column">
                    <v-text-field box class="item" label="First Name"
                      v-model="director.officer.firstName"
                      :rules="directorFirstNameRules"
                      required></v-text-field>
                    <v-text-field box label="Initial" class="item director-initial"
                      v-model="director.officer.middleInitial"
                    ></v-text-field>
                    <v-text-field box class="item" label="Last Name"
                      v-model="director.officer.lastName"
                      :rules="directorLastNameRules"
                      required></v-text-field>
                  </div>
                  <div class="form__row">
                    <v-text-field box label="Street Address"
                      v-model="director.deliveryAddress.streetAddress"
                      :rules="directorStreetRules"
                      required>
                      </v-text-field>
                  </div>
                  <div class="form__row three-column">
                    <v-text-field class="item" box label="City"
                      v-model="director.deliveryAddress.addressCity"
                      :rules="directorCityRules"
                      required>
                    </v-text-field>
                    <v-select class="item" box label="Province"
                      :items="regionList"
                      :rules="directorRegionRules"
                      v-model="director.deliveryAddress.addressRegion">
                    </v-select>
                    <v-text-field class="item" box label="Postal Code"
                      v-model="director.deliveryAddress.postalCode"
                      :rules="directorPostalCodeRules"
                      required>
                    </v-text-field>
                  </div>
                  <div class="form__row">
                    <v-select box label="Country"
                      :items="countryList"
                      v-model="director.deliveryAddress.addressCountry"
                      :rules="directorCountryRules">
                    </v-select>
                  </div>
                  <div class="form__row form__btns">
                    <v-btn color="error" disabled>
                      <span>Remove</span>
                    </v-btn>
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
          v-for="(director, index) in orderBy(directors, 'lastName')"
          v-bind:key="index">
          <div class="meta-container">
            <label>
              <span>{{director.officer.firstName}} </span>
              <span>{{director.officer.middleInitial}} </span>
              <span>{{director.officer.lastName}}</span>
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
              <v-expand-transition>
                <div class="director-info" v-show="activeIndex !== index">
                  <div class="address">
                    <div class="address__row">{{director.deliveryAddress.streetAddress}}</div>
                    <div class="address__row">{{director.deliveryAddress.streetAddressAdditional}}</div>
                    <div class="address__row">
                      <span>{{director.deliveryAddress.addressCity}}</span>
                      <span>&nbsp;{{director.deliveryAddress.addressRegion}}</span>
                      <span>&nbsp;{{director.deliveryAddress.postalCode}}</span>
                    </div>
                    <div class="address__row">{{director.deliveryAddress.addressCountry}}</div>
                  </div>
                    <div class="actions">
                      <v-btn small flat color="primary" :disabled="!agmEntered"
                        v-show="director.isNew"
                        @click="editDirector(index)">
                        <v-icon small>edit</v-icon>
                        <span>Change</span>
                      </v-btn>
                      <v-btn small flat color="primary" :disabled="!agmEntered"
                        v-show="!director.isNew"
                        @click="removeDirector(director)">
                        <v-icon small>{{director.isDirectorActive ? 'close':'undo'}}</v-icon>
                        <span>{{director.isDirectorActive ? 'Cease':'Undo'}}</span>
                      </v-btn>
                    </div>
                </div>
              </v-expand-transition>

              <!-- EDIT director form -->
              <!-- note - this is only used to edit a NEW director; editing existing directors is not supported in the
                  current release -->
              <v-expand-transition>
                <v-form ref="editDirectorForm"
                  v-show="activeIndex === index"
                  v-model="directorFormValid" lazy-validation>
                  <div class="form__row three-column">
                    <v-text-field box label="First Name" class="item"
                      v-model="director.officer.firstName"
                      :rules="directorFirstNameRules"
                      required
                    ></v-text-field>
                    <v-text-field box label="Initial" class="item director-initial"
                      v-model="director.officer.middleInitial"
                    ></v-text-field>
                    <v-text-field box label="Last Name" class="item"
                      v-model="director.officer.lastName"
                      :rules="directorLastNameRules"
                    ></v-text-field>
                  </div>
                  <div class="form__row">
                    <v-text-field box label="Street Address"
                      v-model="director.deliveryAddress.streetAddress"
                      :rules="directorStreetRules"
                      required>
                      </v-text-field>
                  </div>
                  <div class="form__row three-column">
                    <v-text-field class="item" box label="City"
                      v-model="director.deliveryAddress.addressCity"
                      :rules="directorCityRules"
                      required>
                    </v-text-field>
                    <v-select class="item" box label="Province"
                      :items="regionList"
                      :rules="directorRegionRules"
                      v-model="director.deliveryAddress.addressRegion">
                    </v-select>
                    <v-text-field class="item" box label="Postal Code"
                      v-model="director.deliveryAddress.postalCode"
                      :rules="directorPostalCodeRules"
                      required>
                    </v-text-field>
                  </div>
                  <div class="form__row">
                    <v-select box label="Country"
                      :items="countryList"
                      :rules="directorCountryRules"
                      v-model="director.deliveryAddress.addressCountry" >
                    </v-select>
                  </div>
                  <div class="form__row form__btns">
                    <v-btn color="error"
                      :disabled="!director.isNew"
                      @click="deleteDirector(index)">
                      <span>Remove</span>
                    </v-btn>
                    <v-btn class="form-primary-btn" color="primary"
                      @click="cancelEditDirector(index)">
                      Done</v-btn>
                    <v-btn @click="cancelEditDirector(index)">Cancel</v-btn>
                  </div>
                </v-form>
              </v-expand-transition>
              <!-- END edit director form -->
            </div>
          </div>
        </li>
      </ul>
    </v-card>

  </div>
</template>

<script>
import Vue2Filters from 'vue2-filters'
import axios from '../../axios-auth'

export default {
  name: 'Directors.vue',
  mixins: [Vue2Filters.mixin],
  components: {
  },
  data () {
    return {
      directors: [],
      directorsChangeCount: 0, // counter for directors change, to know whether to add fee
      countryList: [
        'Canada'
      ],
      regionList: [
        'BC'
      ],
      showNewDirectorForm: false,
      activeIndex: undefined,
      isEditingDirector: false,
      isDirectorActive: true,
      director: {
        id: '',
        officer: { firstName: '', lastName: '', middleInitial: '' },
        deliveryAddress: {
          streetAddress: '',
          streetAddressAdditional: '',
          addressCity: '',
          addressRegion: '',
          postalCode: '',
          addressCountry: ''
        }
      },
      directorFormValid: true,
      directorFirstNameRules: [
        v => !!v || 'A first name is required'
      ],
      directorLastNameRules: [
        v => !!v || 'A last name is required'
      ],
      directorStreetRules: [
        v => !!v || 'A street address is required'
      ],
      directorCityRules: [
        v => !!v || 'A city is required'
      ],
      directorRegionRules: [
        v => !!v || 'A region is required'
      ],
      directorPostalCodeRules: [
        v => !!v || 'A postal code is required'
      ],
      directorCountryRules: [
        v => !!v || 'A country is required'
      ]
    }
  },
  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
    agmEntered () {
      if (this.$store.state.agmDate) return true
      else if (this.$store.state.noAGM) return true
      else return false
    },
    directorsChange () {
      if (this.directorsChangeCount > 0) return true
      else return false
    }
  },
  methods: {
    getDirectors: function () {
      if (this.corpNum !== null) {
        console.log('got here 2')
        var token = sessionStorage.getItem('KEYCLOAK_TOKEN')
        var url = this.corpNum + '/directors' // todo - deal with year or date
        console.log(url)
        axios.get(url).then(response => {
          console.log(response.data)
          this.directors = response.data.directors
          for (var i = 0; i < this.directors.length; i++) {
            this.directors[i].id = i + 1
            this.directors[i].isNew = false
            this.directors[i].isDirectorActive = true
          }
        }).catch(error => {
          console.log('getDirectors ERROR: ' + error + ' ' + axios.get)
          // TODO - remove this stub data
          this.directors = [
            {
              id: 1,
              isNew: false,
              isDirectorActive: true,
              officer: { firstName: 'Alli', lastName: 'Myers', middleInitial: '' },
              deliveryAddress: {
                streetAddress: '1111 First Street',
                streetAddressAdditional: '',
                addressCity: 'Victoria',
                addressRegion: 'BC',
                postalCode: 'V8A 2G8',
                addressCountry: 'Canada'
              },
              title: 'Pres'
            },
            {
              id: 2,
              isNew: false,
              isDirectorActive: true,
              officer: { firstName: 'Nora', lastName: 'Patton', middleInitial: '' },
              deliveryAddress: {
                streetAddress: '2222 Second Street',
                streetAddressAdditional: '',
                addressCity: 'Victoria',
                addressRegion: 'BC',
                postalCode: 'V8A 2G8',
                addressCountry: 'Canada'
              },
              title: null
            },
            {
              id: 3,
              isNew: false,
              isDirectorActive: true,
              officer: { firstName: 'Phoebe', lastName: 'Jones', middleInitial: '' },
              deliveryAddress: {
                streetAddress: '3333 Third Street',
                streetAddressAdditional: null,
                addressCity: 'Victoria',
                addressRegion: 'BC',
                postalCode: 'V8A 2G8',
                addressCountry: 'Canada'
              },
              title: null
            },
            {
              id: 4,
              isNew: false,
              isDirectorActive: true,
              officer: { firstName: 'Cole', lastName: 'Bryan', middleInitial: '' },
              deliveryAddress: {
                streetAddress: '4444 Fourth Street',
                streetAddressAdditional: null,
                addressCity: 'Victoria',
                addressRegion: 'BC',
                postalCode: 'V8A 2G8',
                addressCountry: 'Canada'
              },
              title: 'Vice Pres'
            }
          ]
        })
      }
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
      if (this.directors[index] === director) {
        this.directors.splice(index, 1)
      } else {
        let found = this.directors.indexOf(director)
        this.directors.splice(found, 1)
        this.directorsChangeCount--
      }
    },

    validateNewDirectorForm: function (index) {
      if (this.$refs.newDirectorForm.validate()) {
        this.pushNewDirectorData()
        this.cancelNewDirector()
        this.directorsChangeCount++
      } else {
        // do nothing - validator handles validation messaging
      }
    },

    pushNewDirectorData: function (index) {
      let newDirector = {
        id: this.directors.length + 1,
        isDirectorActive: true,
        isNew: true,
        officer: {
          firstName: this.director.firstName,
          middleInitial: this.director.middleInitial,
          lastName: this.director.lastName
        },
        deliveryAddress: {
          streetAddress: this.director.streetAddress,
          streetAddressAdditional: this.director.streetAddressAdditional,
          addressCity: this.director.addressCity,
          addressRegion: this.director.addressRegion,
          postalCode: this.director.postalCode,
          addressCountry: this.director.addressCountry
        }
      }
      this.directors.push(newDirector)
    },

    // Remove director
    removeDirector: function (director) {
      console.log('got to removeDirector()')
      // if this is a Cease, add a fee count
      // otherwise it's just undoing a cease or undoing a new director, so remove fee count
      if (director.isDirectorActive) this.directorsChangeCount++
      else this.directorsChangeCount--

      director.isDirectorActive = !director.isDirectorActive
    },

    // Modify Existing Directors
    editDirector: function (index) {
      this.activeIndex = index
      this.cancelNewDirector()
    },

    cancelEditDirector: function (index) {
      this.activeIndex = undefined
    }
  },
  watch: {
    // if we have director changes (add or cease) add a single fee to the filing
    // - when we've made one change, add the fee; when we've removed/undone all changes, remove the fee
    directorsChange: function (val) {
      // emit event back up to parent
      this.$emit('directorsChange', val)
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"

  .v-card
    line-height 1.2rem
    font-size 0.875rem

  .v-btn
    margin 0
    text-transform none

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
        min-width 4rem

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

  // Address Block Layout
  .address
    display flex
    flex-direction column

  .address__row
    flex 1 1 auto

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

  .remove
    color $gray5 !important

  .new-director .meta-container,
  .meta-container.new-director
    flex-flow column nowrap
    > label:first-child
      margin-bottom 1.5rem
</style>
