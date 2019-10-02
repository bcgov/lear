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
          v-bind:class="{ 'remove' : !isActive(director) || !isActionable(director)}"
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
                    <BaseAddress v-bind:address="director.deliveryAddress" />
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
                    v-show="activeIndexCustomCease === index"
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
                    <v-btn @click="cancelEditDirector()">Cancel</v-btn>
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

<script lang="ts">

import { Component, Mixins, Vue, Prop, Watch, Emit } from 'vue-property-decorator'
import axios from '@/axios-auth'
import { mapState, mapGetters } from 'vuex'
// NB: .vue extension is required when importing SFC
// ref: https://github.com/vuejs/vetur/issues/423#issuecomment-340235722
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'
import DateMixin from '@/mixins/date-mixin'
import ExternalMixin from '@/mixins/external-mixin'

// action constants
const APPOINTED = 'appointed'
const CEASED = 'ceased'
const NAMECHANGED = 'nameChanged'
const ADDRESSCHANGED = 'addressChanged'

interface FormType extends Vue {
  reset(): void
  validate(): boolean
}

interface BaseAddressType extends Vue {
  $refs: any
}

@Component({
  components: {
    BaseAddress
  },
  mixins: [DateMixin, ExternalMixin],
  computed: {
    // Property definitions for runtime environment.
    ...mapState(['entityIncNo', 'lastPreLoadFilingDate', 'currentDate', 'currentFilingStatus']),
    ...mapGetters(['lastCODFilingDate'])
  }
})
export default class Directors extends Mixins(DateMixin, ExternalMixin) {
  // To fix "property X does not exist on type Y" errors, annotate types for referenced components.
  // ref: https://github.com/vuejs/vetur/issues/1414
  $refs!: {
    newDirectorForm: FormType,
    baseAddressNew: BaseAddressType,
    editDirectorForm: Array<FormType>,
    baseAddressEdit: Array<BaseAddressType>
  }

  // Props passed into this component.
  @Prop()
  private asOfDate: string

  @Prop({ default: true })
  private componentEnabled: boolean

  // Local properties.
  private directors = []
  private directorsFinal = []
  private directorsOriginal = []
  private countryList: [
    'Canada'
  ]
  private regionList: [
    'BC'
  ]
  private showNewDirectorForm = false
  private draftDate = null
  private showPopup = false
  private activeIndex = -1
  private activeIndexCustomCease = -1
  private activeDirectorToDelete = null
  private cessationDateTemp = null
  private isEditingDirector = false
  private director = {
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
  }
  private inProgressAddress = null
  private editFormShowHide = {
    showAddress: true,
    showName: true,
    showDates: true
  }
  private directorFormValid = true // used for New and Edit forms

  /**
   * Computed value.
   * @returns The array of validations rules for a director's first name.
   */
  private get directorFirstNameRules (): Array<Function> {
    return [
      v => !!v || 'A first name is required'
    ]
  }

  /**
   * Computed value.
   * @returns The array of validations rules for a director's last name.
   */
  private get directorLastNameRules (): Array<Function> {
    return [
      v => !!v || 'A last name is required'
    ]
  }

  /**
   * Computed value.
   * @returns The array of validations rules for a director's street address.
   */
  private get directorStreetRules (): Array<Function> {
    return [
      v => !!v || 'A street address is required'
    ]
  }

  /**
   * Computed value.
   * @returns The array of validations rules for a director's city.
   */
  private get directorCityRules (): Array<Function> {
    return [
      v => !!v || 'A city is required'
    ]
  }

  /**
   * Computed value.
   * @returns The array of validations rules for a director's region.
   */
  private get directorRegionRules (): Array<Function> {
    return [
      v => !!v || 'A region is required'
    ]
  }

  /**
   * Computed value.
   * @returns The array of validations rules for a director's postal code.
   */
  private get directorPostalCodeRules (): Array<Function> {
    return [
      v => !!v || 'A postal code is required'
    ]
  }

  /**
   * Computed value.
   * @returns The array of validations rules for a director's country.
   */
  private get directorCountryRules (): Array<Function> {
    return [
      v => !!v || 'A country is required'
    ]
  }

  // Local definitions of computed properties for static type checking.
  // Use non-null assertion operator to allow use before assignment.
  readonly entityIncNo!: string
  readonly lastPreLoadFilingDate!: string
  readonly currentDate!: string
  readonly currentFilingStatus!: string
  readonly lastCODFilingDate!: string

  /**
   * Computed value.
   * @returns JSON representation of directors data to use as watch trigger for changes to directors.
   */
  private get directorsJson (): string {
    return JSON.stringify(this.directors)
  }

  /**
   * Computed value.
   * One or more actions taken on directors (add, cease) require a single fee, so check if at least one
   * director in the list is marked as requiring a fee.
   * @returns Whether at least one director has a fee applied.
   */
  private get directorsChange (): boolean {
    return this.directors.filter(director => director.isFeeApplied).length > 0
  }

  /**
   * Computed value.
   * @returns The array of validation rules for director appointment date.
   */
  private get directorAppointmentDateRules (): Array<Function> {
    const rules = []
    let cessationDate = null

    rules.push(v => !!v || 'Appointment Date is required')

    // set cessation date for comparison based on which form we're in
    if (this.activeIndex >= 0) {
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
  }

  /**
   * Computed value.
   * @returns The latest of the most recent COD filing and the last pre-load Cobrs filing.
   */
  private get earliestDateToSet (): string {
    let earliestDateToSet = null

    if (this.lastCODFilingDate === null) {
      earliestDateToSet = this.lastPreLoadFilingDate
    } else if (this.compareDates(this.lastCODFilingDate, this.lastPreLoadFilingDate, '>')) {
      earliestDateToSet = this.lastCODFilingDate
    } else {
      earliestDateToSet = this.lastPreLoadFilingDate
    }

    // when earliest date is calculated, inform parent component
    this.emitEarliestDateToSet(earliestDateToSet)
    return earliestDateToSet
  }

  /**
   * Computed value.
   * @returns The array of validation rules for director cessation date.
   */
  private get directorCessationDateRules (): Array<Function> {
    const rules = []
    let appointmentDate = null

    // set appointment date for comparison based on which form we're in
    if (this.activeIndex >= 0) {
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

  /**
   * Lifecycle hook to load initial data.
   */
  private mounted (): void {
    if (this.currentFilingStatus === 'NEW') {
      this.getDirectors()
    }
  }

  /**
   * Local helper to provide a complete address object including missing/blank fields.
   * @returns An address object.
   */
  private formatAddress (address): object {
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
  }

  /**
   * Function called externally to set the draft date.
   * TODO: change this to a prop
   * @param date The draft date to set.
   */
  public setDraftDate (date): void {
    this.draftDate = date
  }

  /**
   * Function called internall and externally to fetch the list of directors.
   * TODO: change this to a prop?
   */
  public getDirectors (): void {
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
              directors[i].isDirectorActionable = (directors[i].cessationDate === null)

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
  }

  /**
   * Local helper to add a new director.
   */
  private addNewDirector (): void {
    this.showNewDirectorForm = true
    this.activeIndex = null
  }

  /**
   * Local helper to cancel adding a new director.
   */
  private cancelNewDirector (): void {
    this.showNewDirectorForm = false
    this.$refs.newDirectorForm.reset()
    this.$refs.baseAddressNew.$refs.addressForm.reset()

    // set form to initial director data again
    this.director.appointmentDate = this.asOfDate
  }

  /**
   * Local helper to show the Delete Director confirmation popup.
   * @param director The director object to delete.
   */
  private showDeleteDirectorConfirmation (director): void {
    this.showPopup = true
    this.activeDirectorToDelete = director
  }

  /**
   * Local helper to delete a director.
   * @param id The id of the director to delete
   */
  private deleteDirector (id): void {
    let newList = this.directors.filter(function (director) {
      return director.id !== id
    })
    this.directors = newList

    this.activeIndex = null
    this.showPopup = false
    this.activeDirectorToDelete = null
  }

  /**
   * Local helper to validate the new director form.
   */
  private validateNewDirectorForm (): void {
    var mainFormIsValid = this.$refs.newDirectorForm.validate()
    var addressFormIsValid = this.$refs.baseAddressNew.$refs.addressForm.validate()
    if (mainFormIsValid && addressFormIsValid) {
      this.pushNewDirectorData()
      this.cancelNewDirector()
    }
    // else do nothing - validator handles validation messaging
  }

  /**
   * Local helper push the current director data into the list.
   */
  private pushNewDirectorData (): void {
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
  }

  /**
   * Local helper to cease a director.
   * @param director The director object to cease.
   */
  private ceaseDirector (director): void {
    // if this is a Cease, apply a fee
    // otherwise it's just undoing a cease or undoing a new director, so remove fee
    if (this.isActive(director)) director.isFeeApplied = true
    else director.isFeeApplied = false

    // reverse "ceased" action
    this.toggleAction(director, CEASED)

    // either set or undo cessation date
    if (director.cessationDate === null) {
      director.cessationDate = this.cessationDateTemp ? this.cessationDateTemp : this.asOfDate
    } else director.cessationDate = null

    // close standalone cessation date picker and reset date
    this.cessationDateTemp = null
    this.activeIndexCustomCease = null
  }

  /**
   * Local helper to edit a director.
   * @param index The index of the director to edit.
   */
  private editDirector (index): void {
    // clear in-progress director data from form in BaseAddress component - ie: start fresh
    this.inProgressAddress = {}

    this.activeIndex = index
    this.cancelNewDirector()
  }

  /**
   * Local helper to edit a director's dates.
   * @param index The index of the director to edit.
   */
  private editDirectorDates (index): void {
    this.editFormShowHide = {
      showAddress: false,
      showName: false,
      showDates: true
    }

    this.editDirector(index)
  }

  /**
   * Local helper to edit a director's name.
   * @param index The index of the director to edit.
   */
  private editDirectorName (index): void {
    this.editFormShowHide = {
      showAddress: false,
      showName: true,
      showDates: false
    }

    this.editDirector(index)
  }

  /**
   * Local helper to edit a director's address.
   * @param index The index of the director to edit.
   */
  private editDirectorAddress (index): void {
    this.editFormShowHide = {
      showAddress: true,
      showName: false,
      showDates: false
    }

    this.editDirector(index)
  }

  /**
   * Local helper to save a director that was edited.
   * @param index The index of the director to save.
   * @param id The id of the director to save.
   */
  private saveEditDirector (index, id): void {
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
  }

  /**
   * Local helper to cancel a director that was edited.
   */
  private cancelEditDirector (): void {
    this.activeIndex = -1

    // reset form show/hide flags
    this.editFormShowHide = {
      showAddress: true,
      showName: true,
      showDates: true
    }
  }

  /**
   * Local helper to watch changes to the address data in BaseAddress component, and to update
   * our inProgressAddress holder. To be used when we want to save the data.
   * @param val The new value.
   */
  private baseAddressWatcher (val): void {
    this.inProgressAddress = val
  }

  /**
   * Function called internally and externally to set all directors.
   * TODO: change this to a prop
   * @param directors The list of directors to set.
   */
  setAllDirectors (directors): void {
    // load data from existing filing
    this.directors = directors
  }

  /**
   * Local helper to check whether a date is not in the future.
   * @param thedate The date to check.
   * @returns Whether the date is not in the future.
   */
  private dateIsNotFuture (thedate): boolean {
    return this.compareDates(thedate, this.currentDate, '<=')
  }

  /**
   * Local helper to get the earliest standalone cease data for the specified director.
   * @param director The director to check.
   * @returns The date.
   */
  private earliestStandaloneCeaseDateToSet (director): string {
    if (this.compareDates(director.appointmentDate, this.earliestDateToSet, '>')) {
      return director.appointmentDate
    } else {
      return this.earliestDateToSet
    }
  }

  /**
   * Local helper to add or remove an action from a director's actions list.
   * @param director The director to change.
   * @param val The action value to add or remove.
   */
  private toggleAction (director, val): void {
    // add or remove action value from actions list
    const index = director.actions.indexOf(val)
    if (index >= 0) director.actions.splice(index)
    else director.actions.push(val)
  }

  /**
   * Local helper to add an action value to a director's actions list, if it doesn't
   * already exist (to ensure no multiples).
   * @param director The director to change.
   * @param val The action value to add.
   */
  private addAction (director, val): void {
    if (director.actions.indexOf(val) < 0) director.actions.push(val)
  }

  /**
   * Local helper to remove an action value from a director's actions list, if it exists.
   * @param director The director to change.
   * @param val The action value to remove.
   */
  private removeAction (director, val): void {
    // remove an action, if it already exists
    director.actions = director.actions.filter(el => el !== val)
  }

  /**
   * Local helper to check if a director was added in this filing.
   * @param director The director to check.
   * @returns Whether the director was appointed.
   */
  private isNew (director): boolean {
    // helper function - was the director added in this filing?
    return (director.actions.indexOf(APPOINTED) >= 0)
  }

  /**
   * Local helper to check if a director is active in this filing.
   * @param director The director to check.
   * @returns Whether the director is active (ie, not ceased).
   */
  private isActive (director): boolean {
    // helper function - is the director active, ie: not ceased?
    return (director.actions.indexOf(CEASED) < 0)
  }

  /**
   * Local helper to check if a director is actionable.
   * @param director The director to check.
   * @returns Whether the director is actionable.
   */
  private isActionable (director): boolean {
    return director.isDirectorActionable !== undefined ? director.isDirectorActionable : true
  }

  /**
   * If we have director changes (add or cease) add a single fee to the filing.
   * - when we've made one change, add the fee
   * - when we've removed/undone all changes, remove the fee
   */
  @Watch('directorsChange')
  private onDirectorsChange (val: boolean): void {
    // emit event back up to parent
    this.emitDirectorsChange(val)
  }

  /**
   * When a director form's validity changes, inform parent component.
   */
  @Watch('directorFormValid')
  private onDirectorFormValid (val: boolean): void {
    this.emitDirectorFormValid(val)
  }

  /**
   * When as-of date changes (from parent component), refresh list of directors.
   */
  @Watch('asOfDate')
  private onAsOfDate (newVal: string, oldVal: string): void {
    if (!(this.currentFilingStatus === 'DRAFT' && (this.draftDate === newVal || oldVal === null))) {
      this.getDirectors()
    }
  }

  /**
   * When directors list content changes, inform parent component of both All Directors and
   * Active Directors (no ceased directors).
   */
  @Watch('directorsJson')
  private onDirectorsJson (): void {
    this.emitAllDirectors(this.directors)
    this.emitActiveDirectors(this.directors.filter(el => el.cessationDate === null))
  }

  /**
   * Emits an event containing the earliest director change date.
   */
  @Emit('earliestDateToSet')
  private emitEarliestDateToSet (val: string): void { }

  /**
   * Emits an event containing this component's change state.
   */
  @Emit('directorsChange')
  private emitDirectorsChange (val: boolean): void { }

  /**
   * Emits an event containing the director form's validity.
   */
  @Emit('directorFormValid')
  private emitDirectorFormValid (val: boolean): void { }

  /**
   * Emits an event containing the complete directors list.
   */
  @Emit('allDirectors')
  private emitAllDirectors (val: any[]): void { }

  /**
   * Emits an event containing the active directors list.
   */
  @Emit('activeDirectors')
  private emitActiveDirectors (val: any[]): void { }
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

<!-- TODO: WHERE DOES THIS BELONG?
<style lang="stylus">
  @import "../../assets/styles/theme.styl"

  .actions__more_actions .v-list__tile
    color $gray6
    font-size 8pt
    height 28px
    font-weight 500
</style>
-->
