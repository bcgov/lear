<template>
  <v-expansion-panels accordion multiple>
    <v-expansion-panel class="align-items-top address-panel" v-for="director in directors" v-bind:key="director.id">
      <v-expansion-panel-header class="panel-header-btn">
        <div class="avatar-container">
          <v-avatar color="primary" size="25">
            <span class="">{{ director.officer.firstName.substring(0,1)}}</span>
          </v-avatar>
        </div>
        <div class="list-item__title">{{ director.officer.firstName }} {{ director.officer.lastName }}</div>
      </v-expansion-panel-header>
      <v-expansion-panel-content>
        <v-list class="pt-0 pb-0">

          <v-list-item>
            <v-list-item-content>
              <v-list-item-title class="mb-2">Delivery Address</v-list-item-title>
              <v-list-item-subtitle>
                <ul class="address-info">
                  <li>{{ director.deliveryAddress.streetAddress }}</li>
                  <li>{{ director.deliveryAddress.addressCity }} {{ director.deliveryAddress.addressRegion }}
                    {{ director.deliveryAddress.postalCode }}</li>
                  <li>{{ director.deliveryAddress.addressCountry }}</li>
                </ul>
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>

          <v-list-item v-if="entityFilter(EntityTypes.BCorp)">
            <v-list-item-content>
              <v-list-item-title class="mb-2">Mailing Address</v-list-item-title>
              <v-list-item-subtitle>
                <div v-if="isSameAddress(director.deliveryAddress, director.mailingAddress)">
                  Same as above
                </div>
                <ul v-else class="address-info">
                  <li>{{ director.mailingAddress.streetAddress }}</li>
                  <li>{{ director.mailingAddress.addressCity }} {{ director.mailingAddress.addressRegion }}
                    {{ director.mailingAddress.postalCode }}</li>
                  <li>{{ director.mailingAddress.addressCountry }}</li>
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

// Vue Libraries
import { Component, Mixins } from 'vue-property-decorator'
import { mapState } from 'vuex'

// Mixins
import { EntityFilterMixin, AddressMixin } from '@/mixins'

// Constants
import { EntityTypes } from '@/enums'

@Component({
  computed: {
    ...mapState(['directors'])
  },
  mixins: [EntityFilterMixin, AddressMixin]
})
export default class DirectorListSm extends Mixins(EntityFilterMixin, AddressMixin) {
  readonly directors: Array<object>

  // EntityTypes Enum
  readonly EntityTypes: {} = EntityTypes
}
</script>

<style lang="scss" scoped>
  @import "../../assets/styles/theme.scss";

  // Variables
  $avatar-width: 2.75rem;

  // Expansion Panel Customization
  .v-expansion-panel-header {
    padding: 1rem;
  }

  .v-expansion-panel-header > .avatar-container {
    flex: 0 0 auto;
    width: $avatar-width;
  }

  ::v-deep .v-expansion-panel-content__wrap {
    padding-right: 1rem;
    padding-left: 1rem;
    padding-bottom: 1rem;
  }

  .v-avatar {
    flex: 0 0 auto;
    color: $gray0;
    font-size: 0.85rem;
  }

  // Director Address Information
  .v-list-item {
    padding: 0;
  }

  .v-list-item__title {
    font-size: 0.875rem;
    font-weight: 400;
  }

  .v-list-item__content {
    padding: 0;
    margin-left: $avatar-width;
  }

  .address-info {
    padding: 0;
    list-style-type: none;
    line-height: 1.25rem;
  }

</style>
