<template>

  <div id="directors">
    <v-card flat>
      <!-- Current Director List -->
      <ul class="list director-list">
        <v-subheader class="director-header">
          <span>Names</span>
          <span>Delivery Address</span>
          <span v-if="entityFilter(EntityTypes.BCorp)">Mailing Address</span>
          <span>Appointed/Elected</span>
        </v-subheader>
        <li class="container"
            :id="'director-' + director.id"
            v-bind:class="{ 'remove' : !isActive(director) || !isActionable(director)}"
            v-for="(director, index) in orderBy(directorSummary, 'id', -1)"
            v-bind:key="index">
          <div class="meta-container">
            <label>
              <span>{{director.officer.firstName}} </span>
              <span>{{director.officer.middleInitial}} </span>
              <span>{{director.officer.lastName}}</span>
              <div class="director-status">
                <v-scale-transition>
                  <v-chip x-small label color="blue" text-color="white"
                          v-show="isNew(director) && !director.cessationDate">
                    New
                  </v-chip>
                </v-scale-transition>
                <v-scale-transition>
                  <v-chip x-small label text-color="rgba(0,0,0,.38)"
                          v-show="!isActive(director) || !isActionable(director)">
                    Ceased
                  </v-chip>
                </v-scale-transition>
                <v-scale-transition>
                  <v-chip x-small label color="blue lighten-2" text-color="white"
                          v-show="isNew(director) && director.cessationDate">
                    Appointed &amp; Ceased
                  </v-chip>
                </v-scale-transition>
                <v-scale-transition>
                  <v-chip x-small label color="blue" text-color="white"
                          v-show="isNameChanged(director)">
                    Name Changed
                  </v-chip>
                </v-scale-transition>
                <v-scale-transition>
                  <v-chip x-small label color="blue" text-color="white"
                          v-show="isAddressChanged(director)">
                    Address Changed
                  </v-chip>
                </v-scale-transition>
              </div>
            </label>
            <div class="meta-container__inner">
              <v-expand-transition>
                <div class="director-info" >
                  <div class="address">
                    <BaseAddress v-bind:address="director.deliveryAddress" />
                  </div>
                  <div class="address same-address" v-if="entityFilter(EntityTypes.BCorp)">
                    <span v-if="isSameAddress(director.deliveryAddress, director.mailingAddress)">
                      Same as Delivery Address
                    </span>
                    <BaseAddress v-else v-bind:address="director.mailingAddress" />
                  </div>
                  <div class="director_dates">
                    <div class="director_dates__date">{{ director.appointmentDate }}</div>
                    <div v-if="director.cessationDate">Ceased</div>
                    <div class="director_dates__date">{{ director.cessationDate }}</div>
                  </div>
                </div>
              </v-expand-transition>
            </div>
          </div>
        </li>
      </ul>
    </v-card>
    <br>

    <!-- Ceased Directors List -->
    <v-btn text small v-if="directorsCeased.length > 0" @click="expand = !expand" class="cease-Btn">
      <v-icon>{{ dropdownIcon() }}</v-icon>Hide Ceased Directors
    </v-btn>
    <v-card flat>
      <v-expand-transition>
          <ul class="list director-list" v-show="expand">
            <li class="container"
                :id="'director-' + director.id"
                v-bind:class="{ 'remove' : !isActive(director) || !isActionable(director)}"
                v-for="(director, index) in orderBy(directorsCeased, 'id', -1)"
                v-bind:key="index">
              <div class="meta-container">
                <label>
                  <span>{{director.officer.firstName}} </span>
                  <span>{{director.officer.middleInitial}} </span>
                  <span>{{director.officer.lastName}}</span>
                  <div class="director-status">
                    <v-scale-transition>
                      <v-chip x-small label color="blue" text-color="white"
                              v-show="isNew(director) && !director.cessationDate">
                        New
                      </v-chip>
                    </v-scale-transition>
                    <v-scale-transition>
                      <v-chip x-small label text-color="rgba(0,0,0,.38)"
                              v-show="!isActive(director) || !isActionable(director)">
                        Ceased
                      </v-chip>
                    </v-scale-transition>
                    <v-scale-transition>
                      <v-chip x-small label color="blue lighten-2" text-color="white"
                              v-show="isNew(director) && director.cessationDate">
                        Appointed &amp; Ceased
                      </v-chip>
                    </v-scale-transition>
                    <v-scale-transition>
                      <v-chip x-small label color="blue" text-color="white"
                              v-show="isNameChanged(director)">
                        Name Changed
                      </v-chip>
                    </v-scale-transition>
                    <v-scale-transition>
                      <v-chip x-small label color="blue" text-color="white"
                              v-show="isAddressChanged(director)">
                        Address Changed
                      </v-chip>
                    </v-scale-transition>
                  </div>
                </label>
                <div class="meta-container__inner">
                  <v-expand-transition>
                    <div class="director-info" >
                      <div class="address">
                        <BaseAddress v-bind:address="director.deliveryAddress" />
                      </div>
                      <div class="address same-address" v-if="entityFilter(EntityTypes.BCorp)">
                        <span v-if="isSameAddress(director.deliveryAddress, director.mailingAddress)">
                          Same as Delivery Address
                        </span>
                        <BaseAddress v-else v-bind:address="director.mailingAddress" />
                      </div>
                      <div class="director_dates">
                        <div class="director_dates__date">{{ director.appointmentDate }}</div>
                        <div v-if="director.cessationDate">Ceased</div>
                        <div class="director_dates__date">{{ director.cessationDate }}</div>
                      </div>
                    </div>
                  </v-expand-transition>
                </div>
              </div>
            </li>
          </ul>
      </v-expand-transition>
    </v-card>
  </div>

</template>

<script lang="ts">
// Libraries
import { Component, Mixins, Prop } from 'vue-property-decorator'

// Components
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'

// Mixins
import { DateMixin, EntityFilterMixin, ExternalMixin, AddressMixin } from '@/mixins'

// Enums
import { EntityTypes } from '@/enums'

// Constants
import { DirectorConst } from '@/constants'

// Interfaces
import { DirectorIF } from '@/interfaces'

@Component({
  components: {
    BaseAddress
  }
})
export default class SummaryDirectors extends Mixins(DateMixin, EntityFilterMixin, ExternalMixin, AddressMixin) {
  @Prop({ default: '' })
  private directors: Array<object>

  // Initialize Director Lists
  private directorSummary: Array<object> = []
  private directorsCeased: Array<object> = []

  // Local Properties
  private expand: boolean = true

  // EntityTypes Enum
  EntityTypes: {} = EntityTypes

  /**
    * On-Created hook to create two new arrays of directors for summary output
    * One array will contain new/changed directors
    * One array will contain all ceased directors
    */
  created (): void {
    // Create a copy of the directors array as to not mutate the original array used in filing
    this.directorSummary = this.directors.slice()

    // Push the ceased Directors to new array & remove them from summary array
    this.directorSummary.forEach((director: DirectorIF.Director) => {
      if (director.actions.includes(DirectorConst.CEASED)) {
        this.directorsCeased.push(director)
        this.directorSummary = this.directorSummary.filter(filterDir => filterDir !== director)
      }
    })
  }

  /**
   * Local method to display the proper icon depending on dropdown state
   * @returns A string to determine icon output
   */
  private dropdownIcon (): string {
    return this.expand ? 'mdi-menu-up' : 'mdi-menu-down'
  }

  /**
   * Local helper to check if a director was added in this filing.
   * @param director The director to check.
   * @returns Whether the director was appointed.
   */
  private isNew (director): boolean {
    // helper function - was the director added in this filing?
    return (director.actions.indexOf(DirectorConst.APPOINTED) >= 0)
  }

  /**
   * Local helper to check if a director has the address changed.
   * @param director The director to check.
   * @returns Whether the director has had the address changed.
   */
  private isAddressChanged (director): boolean {
    return (director.actions.indexOf(DirectorConst.ADDRESSCHANGED) >= 0)
  }

  /**
   * Local helper to check if a director has the name changed.
   * @param director The director to check.
   * @returns Whether the director has had the name changed.
   */
  private isNameChanged (director): boolean {
    return (director.actions.indexOf(DirectorConst.NAMECHANGED) >= 0)
  }

  /**
   * Local helper to check if a director is active in this filing.
   * @param director The director to check.
   * @returns Whether the director is active (ie, not ceased).
   */
  private isActive (director): boolean {
    // helper function - is the director active, ie: not ceased?
    return (director.actions.indexOf(DirectorConst.CEASED) < 0)
  }

  /**
   * Local helper to check if a director is actionable.
   * @param director The director to check.
   * @returns Whether the director is actionable.
   */
  private isActionable (director): boolean {
    return director.isDirectorActionable !== undefined ? director.isDirectorActionable : true
  }
}

</script>

<style lang="scss" scoped>
  @import "../../assets/styles/theme.scss";

  .v-card {
    line-height: 1.2rem;
    font-size: 0.875rem;
  }

  .v-btn {
    margin: 0;
    text-transform: none;
  }

  ul {
    margin: 0;
    padding: 0;
    list-style-type: none;
  }

  .meta-container{
    display: flex;
    flex-flow: column nowrap;
    position: relative;

    > label:first-child{
      font-weight: 500;
    }

    &__inner {
      flex: 1 1 auto;
    }
  }

  @media (min-width: 768px) {
    .meta-container {
      flex-flow: row nowrap;

      > label:first-child {
        flex: 0 0 auto;
        padding-right: 2rem;
        width: 14rem;
      }
    }
  }

  // List Layout
  .list {
    li {
      border-bottom: 1px solid $gray3;
    }
  }

  .form__row.three-column {
    display: flex;
    flex-flow: row nowrap;
    align-items: stretch;
    margin-right: -0.5rem;
    margin-left: -0.5rem;
    .item {
      flex: 1 1 auto;
      flex-basis: 0;
      margin-right: 0.5rem;
      margin-left: 0.5rem;
    }
  }

  // Address Block Layout
  .address {
    display: flex;
    width: 14rem;
  }

  .address__row {
    flex: 1 1 auto;
  }

  // Director Display
  .director-info {
    display: flex;
    color: $gray6;

    .status {
      flex: 1 1 auto;
    }
  }

  .director-initial {
    max-width: 6rem;
  }

  .new-director-btn {
    margin-bottom: 1.5rem !important;

    .v-icon {
      margin-left: -0.5rem;
    }
  }

  // V-chip customization
  .remove, .remove .director-info {
    color: $gray5 !important;
  }

  .new-director .meta-container,
  .meta-container.new-director {
    flex-flow column nowrap
    > label:first-child {
      margin-bottom: 1.5rem;
    }
  }

  .director_dates {
    font-size: 0.8rem;
  }

  .director-header {
    padding: 1.25rem;
    display: flex;
    justify-content: flex-start;
    height: 3rem;
    background-color: rgba(77, 112, 147, 0.15);

    span {
      width: 14rem;
      color: #000014;
      font-size: 0.875rem;
      font-weight: 600;
      line-height: 1.1875rem;
    }
  }

  .editFormStyle {
    border: 1px solid red;
    padding: 1rem;
  }

  .cease-Btn {
    color: #1876D2;
  }

</style>
