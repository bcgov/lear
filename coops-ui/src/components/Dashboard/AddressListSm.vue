<template>
  <v-expansion-panels accordion multiple :value=[0]>
    <!-- Registered Office -->
    <v-expansion-panel class="align-items-top address-panel" id="registered-office-panel">
      <v-expansion-panel-header class="panel-header-btn">
        <div class="list-item__title">Registered Office</div>
      </v-expansion-panel-header>
      <v-expansion-panel-content class="panel-wrapper">
        <v-list class="pt-0 pb-0" v-if="registeredAddress">

          <v-list-item v-if="registeredAddress.deliveryAddress">
            <v-list-item-icon class="address-icon mr-0">
              <v-icon color="primary">mdi-truck</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title class="mb-2">Delivery Address</v-list-item-title>
              <v-list-item-subtitle>
                <ul class="address-info">
                  <li>{{ registeredAddress.deliveryAddress.streetAddress }}</li>
                  <li class="pre-wrap" v-html="registeredAddress.deliveryAddress.streetAddressAdditional"></li>
                  <li>
                    {{ registeredAddress.deliveryAddress.addressCity }}
                    {{ registeredAddress.deliveryAddress.addressRegion }}
                  &nbsp;&nbsp;{{ registeredAddress.deliveryAddress.postalCode}}
                  </li>
                  <li>{{ getCountryName(registeredAddress.deliveryAddress.addressCountry) }}</li>
                </ul>
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>

          <v-list-item v-if="registeredAddress.mailingAddress">
            <v-list-item-icon class="address-icon mr-0">
              <v-icon color="primary">mdi-email-outline</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title class="mb-2">Mailing Address</v-list-item-title>
              <v-list-item-subtitle>
                <div v-if="isSameAddress(registeredAddress.deliveryAddress, registeredAddress.mailingAddress)">
                  Same as above
                </div>
                <ul class="address-info" v-else>
                  <li>{{ registeredAddress.mailingAddress.streetAddress }}</li>
                  <li class="pre-wrap" v-html="registeredAddress.mailingAddress.streetAddressAdditional"></li>
                  <li>
                    {{ registeredAddress.mailingAddress.addressCity }}
                    {{ registeredAddress.mailingAddress.addressRegion }}
                    {{ registeredAddress.mailingAddress.postalCode}}
                  </li>
                  <li>{{ getCountryName(registeredAddress.mailingAddress.addressCountry) }}</li>
                </ul>
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>

        </v-list>
      </v-expansion-panel-content>
    </v-expansion-panel>

    <!--Records Office-->
    <v-expansion-panel
      class="align-items-top address-panel"
      v-if="entityFilter(EntityTypes.BCorp)"
    >
      <v-expansion-panel-header class="panel-header-btn" id="record-office-panel">
        <div class="list-item__title">Record Office</div>
      </v-expansion-panel-header>
      <v-expansion-panel-content class="panel-wrapper">
        <v-list class="pt-0 pb-0" v-if="recordsAddress">

          <v-list-item v-if="recordsAddress.deliveryAddress">
            <v-list-item-icon class="address-icon mr-0">
              <v-icon color="primary">mdi-truck</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title class="mb-2">Delivery Address</v-list-item-title>
              <v-list-item-subtitle>
                <ul class="address-info">
                  <li>{{ recordsAddress.deliveryAddress.streetAddress }}</li>
                  <li class="pre-wrap" v-html="recordsAddress.deliveryAddress.streetAddressAdditional"></li>
                  <li>{{ recordsAddress.deliveryAddress.addressCity }} {{ recordsAddress.deliveryAddress.addressRegion }}
                    &nbsp;&nbsp;{{ recordsAddress.deliveryAddress.postalCode}}</li>
                  <li>{{ getCountryName(recordsAddress.deliveryAddress.addressCountry) }}</li>
                </ul>
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>

          <v-list-item v-if="recordsAddress.mailingAddress">
            <v-list-item-icon class="address-icon mr-0">
              <v-icon color="primary">mdi-email-outline</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title class="mb-2">Mailing Address</v-list-item-title>
              <v-list-item-subtitle>
                <div v-if="isSameAddress(recordsAddress.deliveryAddress, recordsAddress.mailingAddress)">
                  Same as above
                </div>
                <ul class="address-info" v-else>
                  <li>{{ recordsAddress.mailingAddress.streetAddress }}</li>
                  <li class="pre-wrap" v-html="recordsAddress.mailingAddress.streetAddressAdditional"></li>
                  <li>{{ recordsAddress.mailingAddress.addressCity }} {{ recordsAddress.mailingAddress.addressRegion }}
                    &nbsp;&nbsp;{{ recordsAddress.mailingAddress.postalCode}}</li>
                  <li>{{ getCountryName(recordsAddress.mailingAddress.addressCountry) }}</li>
                </ul>
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>

        </v-list>
      </v-expansion-panel-content>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script lang="ts">
// Libraries
import { Component, Mixins } from 'vue-property-decorator'
import { mapState } from 'vuex'
import CountriesProvincesMixin from '@/mixins/countries-provinces-mixin'

// Mixins
import { EntityFilterMixin, AddressMixin } from '@/mixins'

// Enums
import { EntityTypes } from '@/enums'

// Interfaces
import { BaseAddressObjIF } from '@/interfaces/address-interfaces'

@Component({
  mixins: [CountriesProvincesMixin],
  computed: {
    ...mapState(['registeredAddress', 'recordsAddress'])
  }
})

export default class AddressListSm extends Mixins(EntityFilterMixin, AddressMixin) {
  // Base Address properties
  private registeredAddress: BaseAddressObjIF
  private recordsAddress: BaseAddressObjIF

  // EntityTypes Enum
  readonly EntityTypes: {} = EntityTypes
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/theme.scss';

// Variables
$icon-width: 2.75rem;

  .panel-wrapper {
    margin-left: -1.5rem;
  }
  .panel-header-btn {
    padding-left: .85rem;
  }

  .v-list-item {
    padding: 0 1rem;
  }

  .v-list-item__icon {
    margin-top: 0.7rem;
    margin-right: 0;
  }

  .v-list-item__title {
    font-size: 0.875rem;
    font-weight: 400;
  }

.address-icon {
  width: $icon-width;
}

.address-info {
  margin: 0;
  padding: 0;
  list-style-type: none;
}

.pre-wrap {
  white-space: pre-wrap;
}
</style>
