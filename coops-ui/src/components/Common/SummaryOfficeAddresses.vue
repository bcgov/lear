<template>
  <v-card flat>
    <ul class="list address-list">
      <!-- Registered Delivery Address -->
      <li class="container">
        <div class="meta-container">
          <label class="section-header">Registered Office</label>
          <div class="meta-container__inner">
            <label><strong>Delivery Address</strong></label>
            <div class="address-wrapper">
              <delivery-address
                :address="registeredAddress.deliveryAddress"
              />
            </div>
          </div>
        </div>
      </li>

      <!-- Registered Mailing Address -->
      <li class="container">
        <div class="meta-container">
          <label></label>
          <div class="meta-container__inner"
            v-if="!isSame(registeredAddress.deliveryAddress, registeredAddress.mailingAddress)"
          >
            <label><strong>Mailing Address</strong></label>
            <div class="address-wrapper">
              <mailing-address
                :address="registeredAddress.mailingAddress"
              />
            </div>
          </div>
          <span id="sameAsAbove" v-else>
            Mailing Address same as above
          </span>
        </div>
      </li>

      <!-- Records Office Section -->
      <div v-if="!isSame(registeredAddress, recordsAddress)">
        <!-- Records Delivery Address -->
        <li class="container">
          <div class="meta-container">
            <label>Records Office</label>
            <div class="meta-container__inner">
              <label><strong>Delivery Address</strong></label>
              <div class="address-wrapper">
                <delivery-address
                  :address="recordsAddress.deliveryAddress"
                />
              </div>
            </div>
          </div>
        </li>

        <!-- Records Mailing Address -->
        <li class="container">
          <div class="meta-container">
            <label></label>
            <div class="meta-container__inner"
              v-if="!isSame(recordsAddress.deliveryAddress, recordsAddress.mailingAddress)"
            >
              <label>Mailing Address</label>
              <div class="address-wrapper">
                <mailing-address
                  :address="recordsAddress.mailingAddress"
                />
              </div>
            </div>
            <span v-else>
              Mailing Address same as above
            </span>
          </div>
        </li>
      </div>
      <div v-else>
        <li class="container">
          <div class="meta-container">
            <label>Records Office</label>
            <div class="meta-container__inner">
              <span id="sameAsRegistered">
                Same as Registered Office
              </span>
            </div>
          </div>
        </li>
      </div>
    </ul>
  </v-card>
</template>

<script lang="ts">
// Libraries
import { Component, Prop, Mixins } from 'vue-property-decorator'

// Components
import BaseAddress from 'sbc-common-components/src/components/BaseAddress.vue'

// Mixins
import { CommonMixin, EntityFilterMixin } from '@/mixins'

// Interfaces
import { BaseAddressObjIF } from '@/interfaces'

// Enums
import { EntityTypes } from '@/enums'

@Component({
  components: {
    'delivery-address': BaseAddress,
    'mailing-address': BaseAddress
  }
})
export default class SummaryOfficeAddresses extends Mixins(CommonMixin, EntityFilterMixin) {
  /**
   * Registered Office address object passed in from the parent which is pulled from store.
   */
  @Prop({ default: null })
  private registeredAddress: BaseAddressObjIF

  /**
   * Records Office address object passed in from the parent which is pulled from store.
   */
  @Prop({ default: null })
  private recordsAddress: BaseAddressObjIF

  // Entity Enum
  private EntityTypes: {} = EntityTypes
}
</script>

<style lang="scss" scoped>
  @import '../../assets/styles/theme.scss';
  .v-btn {
    margin: 0;
    min-width: 6rem;
    text-transform: none;
  }

  .reset-btn {
    margin-top: 0.5rem;
  }

  .meta-container {
    display: flex;
    flex-flow: column nowrap;
    position: relative;
  }

  .meta-container__inner {
    margin-top: 1rem;
  }

  label:first-child {
    font-weight: 700;
    &__inner {
      flex: 1 1 auto;
    }
  }

  @media (min-width: 768px) {
    .meta-container {
      flex-flow: row nowrap;

      label:first-child {
        flex: 0 0 auto;
        padding-right: 4rem;
        width: 12rem;
      }
    }

    .meta-container__inner {
      margin-top: 0;
    }
  }

  .address-list .form {
    margin-top: 1rem;
  }

  @media (min-width: 768px) {
    .address-list .form {
      margin-top: 0rem
    }
  }

  // Address Block Layout
  .address-wrapper{
    margin-top: .5rem;
  }

  .address-block__actions {
    position: absolute;
    top: 0;
    right: 0;

    .v-btn {
      min-width: 4rem;
    }

    .v-btn + .v-btn {
      margin-left: 0.5rem;
    }
  }

  // Form Row Elements
  .form__row + .form__row {
    margin-top: 0.25rem;
  }

  .form__btns {
    text-align: right;
    display: flex;
    justify-content: flex-end;
    padding: 1rem;

    .v-btn {
      margin: 0;

      + .v-btn {
        margin-left: 0.5rem;
      }
    }
  }

  .form__row.three-column {
    display: flex;
    flex-flow: row nowrap;
    align-items: stretch;
    margin-right: -0.5rem;
    margin-left: -0.5rem;
  }

  .inherit-checkbox {
    margin-top: -3px;
    margin-left: -3px;
    padding: 0;
  }
  .records-inherit-checkbox {
    margin-top: 0rem;
    margin-left: 6rem;
    margin-bottom: -1.5rem;
    padding: 0;

    .v-messages {
      display: none!important;
    }
  }

  // Registered Office Address Form Behavior
  .show-address-form {

    li:first-child {
      padding-bottom: 0;
    }
  }

  ul {
    margin: 0;
    padding: 0;
    list-style-type: none;
  }

  // Editing Address Form

  .address-edit-header {
    display: flex;
    background-color: rgba(1,51,102,0.15);
    padding: 1.25rem;

    address-edit-title {
      font-size: 16px;
      font-weight: bold;
      line-height: 22px;
    }
  }

</style>
