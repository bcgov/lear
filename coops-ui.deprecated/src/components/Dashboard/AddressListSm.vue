<template>
  <div id="address-list-sm">
    <v-expansion-panels accordion multiple :value=[0]>
      <!-- Registered Office -->
      <v-expansion-panel id="registered-office-panel"
        class="align-items-top"
        :class="{ 'address-overlay': coaPending }"
      >
        <v-expansion-panel-header id="registered-office-panel-toggle">
          <div class="list-item__title">Registered Office</div>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="panel-wrapper pt-0 pb-0">
          <v-list class="pt-0 pb-0" v-if="registeredAddress">
            <v-list-item class="delivery-address-list-item"
              v-if="registeredAddress.deliveryAddress"
              :class="{ 'address-overlay': coaPending }"
            >
              <v-list-item-icon class="address-icon mr-0">
                <v-icon color="primary">mdi-truck</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title class="mb-2 address-title">Delivery Address</v-list-item-title>
                <v-list-item-subtitle>
                  <ul class="address-subtitle pre-line">
                    <li class="address-line1">{{ registeredAddress.deliveryAddress.streetAddress }}</li>
                    <li class="address-line2">{{ registeredAddress.deliveryAddress.streetAddressAdditional }}</li>
                    <li class="address-line3">{{ registeredAddress.deliveryAddress.addressCity }}
                                              {{ registeredAddress.deliveryAddress.addressRegion }}
                                              {{ registeredAddress.deliveryAddress.postalCode }}</li>
                    <li class="address-line4">
                      <span>{{ getCountryName(registeredAddress.deliveryAddress.addressCountry) }}</span>
                    </li>
                  </ul>
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>

            <v-list-item class="mailing-address-list-item"
              v-if="registeredAddress.mailingAddress"
              :class="{ 'address-overlay': coaPending }"
            >
              <v-list-item-icon class="address-icon mr-0">
                <v-icon color="primary">mdi-email-outline</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title class="mb-2 address-title">Mailing Address</v-list-item-title>
                <v-list-item-subtitle>
                  <div class="same-as-above"
                    v-if="isSame(registeredAddress.deliveryAddress, registeredAddress.mailingAddress)"
                  >
                    <span>Same as above</span>
                  </div>
                  <ul v-else class="address-subtitle pre-line">
                    <li class="address-line1">{{ registeredAddress.mailingAddress.streetAddress }}</li>
                    <li class="address-line2">{{ registeredAddress.mailingAddress.streetAddressAdditional }}</li>
                    <li class="address-line3">{{ registeredAddress.mailingAddress.addressCity }}
                                              {{ registeredAddress.mailingAddress.addressRegion }}
                                              {{ registeredAddress.mailingAddress.postalCode }}</li>
                    <li class="address-line4">
                      <span>{{ getCountryName(registeredAddress.mailingAddress.addressCountry) }}</span>
                    </li>
                  </ul>
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-expansion-panel-content>
      </v-expansion-panel>

      <!--Records Office-->
      <v-expansion-panel id="records-office-panel"
        v-if="entityFilter(EntityTypes.BCOMP)"
        class="align-items-top"
        :class="{ 'address-overlay': coaPending }"
      >
        <v-expansion-panel-header id="records-office-panel-toggle">
          <div class="list-item__title">Records Office</div>
        </v-expansion-panel-header>

        <v-expansion-panel-content class="panel-wrapper">
          <v-list class="pt-0 pb-0" v-if="recordsAddress">
            <v-list-item class="delivery-address-list-item"
              v-if="recordsAddress.deliveryAddress"
              :class="{ 'address-overlay': coaPending }"
            >
              <v-list-item-icon class="address-icon mr-0">
                <v-icon color="primary">mdi-truck</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title class="mb-2 address-title">Delivery Address</v-list-item-title>
                <v-list-item-subtitle>
                  <ul class="address-subtitle pre-line">
                    <li class="address-line1">{{ recordsAddress.deliveryAddress.streetAddress }}</li>
                    <li class="address-line2">{{ recordsAddress.deliveryAddress.streetAddressAdditional }}</li>
                    <li class="address-line3">{{ recordsAddress.deliveryAddress.addressCity }}
                                              {{ recordsAddress.deliveryAddress.addressRegion }}
                                              {{ recordsAddress.deliveryAddress.postalCode }}</li>
                    <li class="address-line4">
                      <span>{{ getCountryName(recordsAddress.deliveryAddress.addressCountry) }}</span>
                    </li>
                  </ul>
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>

            <v-list-item class="mailing-address-list-item"
              v-if="recordsAddress.mailingAddress"
              :class="{ 'address-overlay': coaPending }"
            >
              <v-list-item-icon class="address-icon mr-0">
                <v-icon color="primary">mdi-email-outline</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title class="mb-2 address-title">Mailing Address</v-list-item-title>
                <v-list-item-subtitle>
                  <div class="same-as-above"
                    v-if="isSame(recordsAddress.deliveryAddress, recordsAddress.mailingAddress)"
                  >
                    <span>Same as above</span>
                  </div>
                  <ul v-else class="address-subtitle pre-line">
                    <li class="address-line1">{{ recordsAddress.mailingAddress.streetAddress }}</li>
                    <li class="address-line2">{{ recordsAddress.mailingAddress.streetAddressAdditional }}</li>
                    <li class="address-line3">{{ recordsAddress.mailingAddress.addressCity }}
                                              {{ recordsAddress.mailingAddress.addressRegion }}
                                              {{ recordsAddress.mailingAddress.postalCode }}</li>
                    <li class="address-line4">
                      <span>{{ getCountryName(recordsAddress.mailingAddress.addressCountry) }}</span>
                    </li>
                  </ul>
                </v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script lang="ts">
// Libraries
import { Component, Mixins, Prop } from 'vue-property-decorator'
import { mapState } from 'vuex'

// Mixins
import { EntityFilterMixin, CommonMixin, CountriesProvincesMixin } from '@/mixins'

// Enums
import { EntityTypes } from '@/enums'

// Interfaces
import { BaseAddressObjIF } from '@/interfaces'

@Component({
  computed: {
    ...mapState(['registeredAddress', 'recordsAddress'])
  }
})
export default class AddressListSm extends Mixins(EntityFilterMixin, CommonMixin, CountriesProvincesMixin) {
  // Base Address properties
  private registeredAddress: BaseAddressObjIF
  private recordsAddress: BaseAddressObjIF

  // Pending Prop
  @Prop({ default: false })
  private coaPending: boolean

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

#registered-office-panel-toggle,
#records-office-panel-toggle {
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

.v-list-item__subtitle {
  line-height: 1.25rem;
}

.v-list-item__content {
  padding: 0 0 1rem 0;
}

.address-icon {
  width: $icon-width;
  margin-top: 0;
}

.address-subtitle {
  margin: 0;
  padding: 0;
  list-style-type: none;
}

.address-overlay {
  background-color: rgba(255, 235, 59, .1)!important;
}
</style>
