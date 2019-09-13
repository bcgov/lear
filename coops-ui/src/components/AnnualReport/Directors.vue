<template>
  <div id="directors">

    <!-- delete new director - confirmation popup -->
    <v-dialog v-model="showPopup" width="30rem">
      <v-card>
        <v-card-text>
          Are you sure you want to remove
            <span v-if="activeDirectorToDelete" class="font-weight-bold">
              <span>{{activeDirectorToDelete.officer.firstName}} </span>
              <span>{{activeDirectorToDelete.officer.middleInitial}} </span>
              <span>{{activeDirectorToDelete.officer.lastName}}</span>
            </span>
          from your Directors list?
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="deleteDirector(activeDirectorToDelete.id)">
           Remove
          </v-btn>
          <v-btn color="default" @click="showPopup = false; activeDirectorToDelete = null">
           Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-expand-transition>
      <div v-show="!showNewDirectorForm">
        <v-btn class="new-director-btn" outline color="primary" :disabled="!componentEnabled"
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
                    <v-text-field box class="item" label="First Name" id="new-director__first-name"
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

                  <BaseAddress ref="baseAddressNew"
                    v-bind:address="director.deliveryAddress"
                    v-bind:editing="true"
                    @update:address="baseAddressWatcher"
                  />

                  <!-- removed until release 2 -->
                  <!--
                  <div class="form__row three-column new-director__dates">
                    <v-menu
                      :nudge-right="40"
                      lazy
                      transition="scale-transition"
                      offset-y
                      full-width
                      min-width="18rem">
                      <template v-slot:activator="{ on }">
                        <v-text-field box class="item" label="Appointment / Election Date"
                          id="new-director__appointment-date"
                          v-model="director.appointmentDate"
                          hint="YYYY/MM/DD"
                          append-icon="event"
                          v-on="on"
                          :rules="directorAppointmentDateRules"
                        >
                        </v-text-field>
                      </template>
                      <v-date-picker
                        id="new-director__appointment-date__datepicker"
                        v-model="director.appointmentDate"
                        :min="earliestDateToSet"
                        :max="currentDate"
                        no-title>
                      </v-date-picker>
                    </v-menu>

                    <v-menu
                      :nudge-right="40"
                      lazy
                      transition="scale-transition"
                      offset-y
                      full-width
                      min-width="18rem">
                      <template v-slot:activator="{ on }">
                        <v-text-field class="item" ref="newDirectorCessationDate"
                          id="new-director__cessation-date"
                          v-model="director.cessationDate"
                          label="Cessation Date"
                          hint="YYYY/MM/DD"
                          append-icon="event"
                          v-on="on"
                          :rules="directorCessationDateRules"
                          box>
                        </v-text-field>
                      </template>
                      <v-date-picker
                        id="new-director__cessation-date__datepicker"
                        v-model="director.cessationDate"
                        :min="earliestDateToSet"
                        :max="currentDate"
                        no-title>
                      </v-date-picker>
                    </v-menu>
                  </div>
                  -->

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
          :id="'director-' + director.id"
          v-bind:class="{ 'remove' : !isActive(director)  || !isActionable(director)}"
          v-for="(director, index) in orderBy(directors, 'id', -1)"
          v-bind:key="index">
          <div class="meta-container">
            <label>
              <span>{{director.officer.firstName}} </span>
              <span>{{director.officer.middleInitial}} </span>
              <span>{{director.officer.lastName}}</span>
              <div class="director-status">
                <v-scale-transition>
                  <v-chip small label disabled color="blue" text-color="white"
                          v-show="isNew(director) && !director.cessationDate">
                    New
                  </v-chip>
                </v-scale-transition>
                <v-scale-transition>
                  <v-chip small label disabled v-show="!isActive(director) || !isActionable(director)">
                    Ceased
                  </v-chip>
                </v-scale-transition>
                <v-scale-transition>
                  <v-chip small label disabled color="blue lighten-2" text-color="white"
                          v-show="isNew(director) && director.cessationDate">
                    Appointed & Ceased
                  </v-chip>
                </v-scale-transition>
              </div>
            </label>
            <div class="meta-container__inner">
              <v-expand-transition>
                <div class="director-info" v-show="activeIndex !== index">
                  <div class="address">
                    <BaseAddress v-bind:address="director.deliveryAddress"  />
                  </div>
                  <div class="director_dates">
                    <div>Appointed/Elected</div>
                    <div class="director_dates__date">{{ director.appointmentDate }}</div>
                    <div v-if="director.cessationDate">Ceased</div>
                    <div class="director_dates__date">{{ director.cessationDate }}</div>
                  </div>
                  <div class="actions" v-show="isActionable(director)">

                    <!-- Edit menu -->
                    <span v-show="isNew(director)">
                      <v-btn small flat color="primary" :disabled="!componentEnabled"
                        :id="'director-' + director.id + '-change-btn'"
                        @click="editDirector(index)">
                        <v-icon small>edit</v-icon>
                        <span>Edit</span>
                      </v-btn>

                      <!-- more actions menu -->
                      <!-- removed until release 2 -->
                      <!--
                      <v-menu offset-y>
                        <template v-slot:activator="{ on }">
                          <v-btn flat small class="actions__more-actions__btn"
                            v-on="on"
                          >
                            <v-icon>arrow_drop_down</v-icon>
                          </v-btn>
                        </template>
                        <v-list class="actions__more_actions">
                          <v-list-tile @click="showDeleteDirectorConfirmation(director)">
                            <v-list-tile-title>Remove</v-list-tile-title>
                          </v-list-tile>
                        </v-list>
                      </v-menu>
                      -->
                    </span>

                    <!-- Cease menu -->
                    <span v-show="!isNew(director)">
                      <v-btn small flat color="primary" :disabled="!componentEnabled"
                        class="cease-btn"
                        :id="'director-' + director.id + '-cease-btn'"
                        @click="ceaseDirector(director)">
                        <v-icon small>{{isActive(director) ? 'close':'undo'}}</v-icon>
                        <span>{{isActive(director) ? 'Cease':'Undo'}}</span>
                      </v-btn>
                      <!-- more actions menu -->
                      <!-- removed until release 2 -->
                      <!--
                      <span v-show="isActive(director)">
                        <v-menu offset-y>
                          <template v-slot:activator="{ on }">
                            <v-btn flat small class="actions__more-actions__btn"
                              v-on="on"
                            >
                              <v-icon>arrow_drop_down</v-icon>
                            </v-btn>
                          </template>
                          <v-list class="actions__more_actions">
                            <v-list-tile @click="cessationDateTemp = asOfDate; activeIndexCustomCease = index;">
                              <v-list-tile-title>Set custom cessation date</v-list-tile-title>
                            </v-list-tile>
                            <v-list-tile @click="editDirectorAddress(index)">
                              <v-list-tile-title>Change address</v-list-tile-title>
                            </v-list-tile>
                            <v-list-tile @click="editDirectorName(index)">
                              <v-list-tile-title>Change of legal name</v-list-tile-title>
                            </v-list-tile>
                          </v-list>
                        </v-menu>
                      </span>
                      -->
                    </span>
                  </div>

                  <!-- standalone Cease date picker -->
                  <v-date-picker
                    class="standalone__cessation-date__datepicker"
                    v-model="cessationDateTemp"
                    v-show="activeIndexCustomCease == index"
                    no-title
                    :min="earliestStandaloneCeaseDateToSet(director)"
                    :max="currentDate"
                  >
                    <v-btn text color="primary" @click="activeIndexCustomCease = null">Cancel</v-btn>
                    <v-btn text color="primary" @click="ceaseDirector(director)">OK</v-btn>
                  </v-date-picker>

                </div>
              </v-expand-transition>

              <!-- EDIT director form -->
              <v-expand-transition>
                <v-form ref="editDirectorForm"
                  v-show="activeIndex === index"
                  v-model="directorFormValid" lazy-validation>
                  <div class="form__row three-column" v-show="editFormShowHide.showName">
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

                  <BaseAddress ref="baseAddressEdit"
                    v-show="editFormShowHide.showAddress"
                    v-bind:address="director.deliveryAddress"
                    v-bind:editing="true"
                    @update:address="baseAddressWatcher"
                  />

                  <!-- removed until release 2 -->
                  <!--
                  <div class="form__row three-column edit-director__dates" v-show="editFormShowHide.showDates">
                    <v-menu
                      :nudge-right="40"
                      lazy
                      transition="scale-transition"
                      offset-y
                      full-width
                      min-width="18rem">
                      <template v-slot:activator="{ on }">
                        <v-text-field
                          class="item edit-director__appointment-date"
                          v-model="director.appointmentDate"
                          label="Apointment / Election Date"
                          hint="YYYY/MM/DD"
                          append-icon="event"
                          v-on="on"
                          :rules="directorAppointmentDateRules"
                          box>
                        </v-text-field>
                      </template>
                      <v-date-picker
                        class="edit-director__appointment-date__datepicker"
                        v-model="director.appointmentDate"
                        :min="earliestDateToSet"
                        :max="currentDate"
                        no-title>
                      </v-date-picker>
                    </v-menu>

                    <v-menu
                      :nudge-right="40"
                      lazy
                      transition="scale-transition"
                      offset-y
                      full-width
                      min-width="18rem">
                      <template v-slot:activator="{ on }">
                        <v-text-field class="item edit-director__cessation-date"
                          v-model="director.cessationDate"
                          label="Cessation Date"
                          hint="YYYY/MM/DD"
                          append-icon="event"
                          v-on="on"
                          :rules="directorCessationDateRules"
                          box>
                        </v-text-field>
                      </template>
                      <v-date-picker
                        class="edit-director__cessation-date__datepicker"
                        v-model="director.cessationDate"
                        :min="earliestDateToSet"
                        :max="currentDate"
                        no-title>
                      </v-date-picker>
                    </v-menu>
                  </div>
                  -->

                  <div class="form__row form__btns">
                    <v-btn color="error"
                      v-show="isNew(director)"
                      @click="deleteDirector(director.id)">
                      <span>Remove</span>
                    </v-btn>
                    <v-btn class="form-primary-btn" color="primary"
                      @click="saveEditDirector(index, director.id)">
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
import axios from '@/axios-auth'
import { mapState, mapGetters } from 'vuex'
import BaseAddress from 'sbc-common-components/src/components/BaseAddress'
import DateUtils from '@/date-utils'

// action constants
const APPOINTED = 'appointed'
const CEASED = 'ceased'
const NAMECHANGED = 'nameChanged'
const ADDRESSCHANGED = 'addressChanged'

export default {
  name: 'Directors',

  mixins: [Vue2Filters.mixin, DateUtils],

  components: {
    BaseAddress
  },
  props: {
    asOfDate: String,
    componentEnabled: {
      type: Boolean,
      default: true
    }
  },
  data () {
    return {
      directors: [],
      directorsFinal: [],
      directorsOriginal: [],
      countryList: [
        'Canada'
      ],
      regionList: [
        'BC'
      ],
      showNewDirectorForm: false,
      draftDate: null,
      showPopup: false,
      activeIndex: undefined,
      activeIndexCustomCease: undefined,
      activeDirectorToDelete: null,
      cessationDateTemp: null,
      isEditingDirector: false,
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
        },
        appointmentDate: this.asOfDate,
        cessationDate: null,
        cessationDateTemp: null
      },
      inProgressAddress: null,
      editFormShowHide: {
        showAddress: true,
        showName: true,
        showDates: true
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
    ...mapState(['entityIncNo', 'lastPreLoadFilingDate', 'currentDate', 'currentFilingStatus']),

    ...mapGetters(['lastCODFilingDate']),

    directors_json () {
      // json representation of directors data to use as watch trigger for changes to directors
      return JSON.stringify(this.directors)
    },

    directorsChange () {
      // One or more actions taken on directors (add, cease) require a single fee, so check how many directors in the
      // list are marked as requiring a fee.
      return this.directors.filter(director => director.isFeeApplied).length > 0
    },

    directorAppointmentDateRules () {
      const rules = []
      let cessationDate = null

      rules.push(v => !!v || 'Appointment Date is required')

      // set cessation date for comparison based on which form we're in
      if (this.activeIndex !== undefined && this.activeIndex !== null) {
        cessationDate = document
          .getElementsByClassName('edit-director__cessation-date')[this.activeIndex]
          .getElementsByTagName('input')[0].value
      } else if (this.showNewDirectorForm) {
        cessationDate = this.director.cessationDate
      }

      // appointment date must be before cessation date
      const rule1 =
        v => this.compareDates(v, cessationDate, '<') || 'Appointment Date must be before Cessation Date'

      rules.push(rule1)

      // appointment date must be in the past (or today)
      const rule2 =
        v => this.dateIsNotFuture(v) || 'Appointment Date cannot be in the future'

      rules.push(rule2)

      return rules
    },

    earliestDateToSet () {
      // return the latest of the most recent COD filing and the last pre-load Cobrs filing
      let earliestDateToSet = null

      if (this.lastCODFilingDate === null) {
        earliestDateToSet = this.lastPreLoadFilingDate
      } else if (this.compareDates(this.lastCODFilingDate, this.lastPreLoadFilingDate, '>')) {
        earliestDateToSet = this.lastCODFilingDate
      } else {
        earliestDateToSet = this.lastPreLoadFilingDate
      }

      // when earliest date is calculated, emit it back up for display
      this.$emit('earliestDateToSet', earliestDateToSet)
      return earliestDateToSet
    },

    directorCessationDateRules () {
      const rules = []
      let appointmentDate = null

      // set appointment date for comparison based on which form we're in
      if (this.activeIndex !== undefined && this.activeIndex !== null) {
        appointmentDate = document
          .getElementsByClassName('edit-director__appointment-date')[this.activeIndex]
          .getElementsByTagName('input')[0].value
      } else if (this.showNewDirectorForm) {
        appointmentDate = this.director.appointmentDate
      }

      // cessation date must be after appointment date
      const rule1 =
        v => this.compareDates(v, appointmentDate, '>') || 'Cessation Date must be after Appointment Date'

      rules.push(rule1)

      // cessation date must be in the past (or today)
      const rule2 =
        v => this.dateIsNotFuture(v) || 'Cessation Date cannot be in the future'

      rules.push(rule2)

      return rules
    }
  },

  mounted () {
    if (this.currentFilingStatus === 'NEW') {
      this.getDirectors()
    }
  },

  methods: {
    formatAddress (address) {
      return {
        'addressCity': address.addressCity || '',
        'addressCountry': address.addressCountry || '',
        'addressRegion': address.addressRegion || '',
        'addressType': address.addressType || '',
        'deliveryInstructions': address.deliveryInstructions || '',
        'postalCode': address.postalCode || '',
        'streetAddress': address.streetAddress || '',
        'streetAddressAdditional': address.streetAddressAdditional || ''
      }
    },

    setDraftDate: function (date) {
      this.draftDate = date
    },

    getDirectors: function () {
      if (this.entityIncNo && this.asOfDate) {
        var url = this.entityIncNo + '/directors?date=' + this.asOfDate
        axios.get(url)
          .then(response => {
            if (response && response.data && response.data.directors) {
              // note - director list manipulated locally here (attributes added), THEN saved to this.directors,
              // otherwise new attributes are not reflected in initial draw of HTML list.

              var directors = response.data.directors
              for (var i = 0; i < directors.length; i++) {
                directors[i].id = i + 1
                directors[i].isFeeApplied = directors[i].isFeeApplied !== undefined ? directors[i].isFeeApplied : false
                directors[i].isDirectorActionable = directors[i].cessationDate == null

                directors[i].actions = []

                // if there is no officer middle initial field, add it with blank data
                if (!directors[i].officer.hasOwnProperty('middleInitial')) directors[i].officer.middleInitial = ''

                // save previous officer name data for COLIN to use when updating record
                directors[i].officer.prevFirstName = directors[i].officer.firstName
                directors[i].officer.prevLastName = directors[i].officer.lastName
                directors[i].officer.prevMiddleInitial = directors[i].officer.middleInitial

                // ensure there is complete address data including missing/blank fields
                directors[i].deliveryAddress = this.formatAddress(directors[i].deliveryAddress)
              }

              // save to component data now that extra attributes are added
              this.directors = directors

              // save version of directors before changes (deep copy, not reference)
              this.directorsOriginal = JSON.parse(JSON.stringify(this.directors))
            } else {
              console.log('getDirectors() error - invalid response data')
            }
          })
          .catch(error => console.error('getDirectors() error =', error))
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
      this.$refs.baseAddressNew.$refs.addressForm.reset()

      // set form to initial director data again
      this.director.appointmentDate = this.asOfDate
    },

    showDeleteDirectorConfirmation: function (director) {
      this.showPopup = true
      this.activeDirectorToDelete = director
    },

    deleteDirector: function (id) {
      let newList = this.directors.filter(function (director) {
        return director.id !== id
      })
      this.directors = newList

      this.activeIndex = null
      this.showPopup = false
      this.activeDirectorToDelete = null
    },

    validateNewDirectorForm: function () {
      var mainFormIsValid = this.$refs.newDirectorForm.validate()
      var addressFormIsValid = this.$refs.baseAddressNew.$refs.addressForm.validate()
      if (mainFormIsValid && addressFormIsValid) {
        this.pushNewDirectorData()
        this.cancelNewDirector()
      } else {
        // do nothing - validator handles validation messaging
      }
    },

    pushNewDirectorData: function () {
      let newDirector = {
        actions: [APPOINTED],
        id: this.directors.length + 1,
        isDirectorActionable: true,
        isFeeApplied: true,
        officer: {
          firstName: this.director.officer.firstName,
          middleInitial: this.director.officer.middleInitial,
          lastName: this.director.officer.lastName
        },
        deliveryAddress: {
          streetAddress: this.inProgressAddress.streetAddress,
          streetAddressAdditional: this.inProgressAddress.streetAddressAdditional,
          addressCity: this.inProgressAddress.addressCity,
          addressRegion: this.inProgressAddress.addressRegion,
          postalCode: this.inProgressAddress.postalCode,
          addressCountry: this.inProgressAddress.addressCountry
        },
        appointmentDate: this.asOfDate, // when implemented: this.director.appointmentDate,
        cessationDate: null // when implemented: this.director.cessationDate
      }

      // if there is also a cease date on this new director, add the ceased action
      if (this.director.cessationDate !== null && this.director.cessationDate !== undefined) {
        this.addAction(newDirector, CEASED)
      }

      this.directors.push(newDirector)
    },

    // Cease director
    ceaseDirector: function (director) {
      // if this is a Cease, apply a fee
      // otherwise it's just undoing a cease or undoing a new director, so remove fee
      if (this.isActive(director)) director.isFeeApplied = true
      else director.isFeeApplied = false

      // reverse "ceased" action
      this.toggleAction(director, CEASED)

      // either set or undo cessation date
      if (director.cessationDate == null) {
        director.cessationDate = this.cessationDateTemp ? this.cessationDateTemp : this.asOfDate
      } else director.cessationDate = null

      // close standalone cessation date picker and reset date
      this.cessationDateTemp = null
      this.activeIndexCustomCease = null
    },

    // Modify Existing Directors
    editDirector: function (index) {
      // clear in-progress director data from form in BaseAddress component - ie: start fresh
      this.inProgressAddress = {}

      this.activeIndex = index
      this.cancelNewDirector()
    },
    editDirectorDates: function (index) {
      this.editFormShowHide = {
        showAddress: false,
        showName: false,
        showDates: true
      }

      this.editDirector(index)
    },
    editDirectorName: function (index) {
      this.editFormShowHide = {
        showAddress: false,
        showName: true,
        showDates: false
      }

      this.editDirector(index)
    },
    editDirectorAddress: function (index) {
      this.editFormShowHide = {
        showAddress: true,
        showName: false,
        showDates: false
      }

      this.editDirector(index)
    },

    saveEditDirector: function (index, id) {
      // get current director
      let director = this.directors[id - 1]

      var mainFormIsValid = this.$refs.editDirectorForm[index].validate()
      var addressFormIsValid = this.$refs.baseAddressEdit[index].$refs.addressForm.validate()
      if (mainFormIsValid && addressFormIsValid) {
        // save data from BaseAddress component
        // - only save address if a change was made, ie there is an in-progress address from the component
        if (!Object.values(this.inProgressAddress).every(el => el === undefined)) {
          director.deliveryAddress = this.inProgressAddress
        }

        /* COMPARE changes to original director data, for existing directors */
        if (director.actions.indexOf(APPOINTED) < 0) {
          const origDirector = this.directorsOriginal.filter(el => el.id === id)[0]

          // check whether address has changed
          if (JSON.stringify(origDirector.deliveryAddress) !== JSON.stringify(director.deliveryAddress)) {
            this.addAction(director, ADDRESSCHANGED)
          } else {
            this.removeAction(director, ADDRESSCHANGED)
          }

          // check whether name has changed
          if (JSON.stringify(origDirector.officer) !== JSON.stringify(director.officer)) {
            this.addAction(director, NAMECHANGED)
          } else {
            this.removeAction(director, NAMECHANGED)
          }
        }

        this.cancelEditDirector()
      } else {
        // do nothing - validator handles validation messaging
      }
    },

    cancelEditDirector: function (index) {
      this.activeIndex = undefined

      // reset form show/hide flags
      this.editFormShowHide = {
        showAddress: true,
        showName: true,
        showDates: true
      }
    },

    baseAddressWatcher: function (val) {
      // Watches changes to the address data in BaseAddress component, and updates our inProgressAddress holder, to be
      // used when we want to save the data.
      this.inProgressAddress = val
    },

    setAllDirectors (directors) {
      // load data from existing filing
      this.directors = directors
    },

    // util function to check whether a date is in the future
    dateIsNotFuture (thedate) {
      return this.compareDates(thedate, this.currentDate, '<=')
    },

    earliestStandaloneCeaseDateToSet (director) {
      if (this.compareDates(director.appointmentDate, this.earliestDateToSet, '>')) {
        return director.appointmentDate
      } else {
        return this.earliestDateToSet
      }
    },
    toggleAction (director, val) {
      // add or remove action value from actions list
      const index = director.actions.indexOf(val)
      if (index >= 0) director.actions.splice(index)
      else director.actions.push(val)
    },
    addAction (director, val) {
      // add an action, if it doesn't already exist; ensures no multiples
      if (director.actions.indexOf(val) < 0) director.actions.push(val)
    },
    removeAction (director, val) {
      // remove an action, if it already exists
      director.actions = director.actions.filter(el => el !== val)
    },
    isNew (director) {
      // helper function - was the director added in this filing?
      if (director.actions.indexOf(APPOINTED) >= 0) return true
      else return false
    },
    isActive (director) {
      // helper function - is the director active, ie: not ceased?
      if (director.actions.indexOf(CEASED) < 0) return true
      else return false
    },
    isActionable (director) {
      return director.isDirectorActionable !== undefined ? director.isDirectorActionable : true
    }
  },

  watch: {
    // if we have director changes (add or cease) add a single fee to the filing
    // - when we've made one change, add the fee; when we've removed/undone all changes, remove the fee
    directorsChange: function (val) {
      // emit event back up to parent
      this.$emit('directorsChange', val)
    },
    directorFormValid (val) {
      this.$emit('directorFormValid', val)
    },
    // when as-of date changes (from parent component) refresh list of directors
    asOfDate (newVal, oldVal) {
      if (!(this.currentFilingStatus === 'DRAFT' && (this.draftDate === newVal || oldVal == null))) {
        this.getDirectors()
      }
    },
    directors_json () {
      // emit data to two events - allDirectors and activeDirectors (no ceased directors)
      this.$emit('allDirectors', this.directors)
      this.$emit('activeDirectors', this.directors.filter(el => el.cessationDate === null))
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
    width 10rem

  .address__row
    flex 1 1 auto

  // Director Display
  .director-info
    display flex
    color $gray6

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

  .remove, .remove .director-info
    color $gray5 !important

  .new-director .meta-container,
  .meta-container.new-director
    flex-flow column nowrap
    > label:first-child
      margin-bottom 1.5rem

  .director_dates
    font-size 0.8rem
    margin-left 100px

    .director_dates__date
      margin-left 20px

  .actions .v-btn.actions__more-actions__btn
    min-width 25px
    border-left 1px solid $gray3
    border-radius 0
    margin-left 5px !important
    padding 0 5px
    color $gray6

  .standalone__cessation-date__datepicker
    margin-top 25px
    right 0
    position absolute
    z-index 99
</style>

<style lang="stylus">
  @import "../../assets/styles/theme.styl"

  .actions__more_actions .v-list__tile
    color $gray6
    font-size 8pt
    height 28px
    font-weight 500
</style>
