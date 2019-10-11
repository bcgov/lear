<template>
  <v-expansion-panels class="list list-container" :accordion=true :multiple=true>
    <v-expansion-panel class="address-panel" v-for="director in directors" v-bind:key="director.id">
      <v-expansion-panel-header>
        <v-avatar color="primary" size="25">
        <span class="">{{ director.officer.firstName.substring(0,1)}}</span>
        </v-avatar>
        <div class="list-item__title">{{ director.officer.firstName }} {{ director.officer.lastName }}</div>
      </v-expansion-panel-header>
      <v-expansion-panel-content class="list-container-content">
        <li class="list-item" >
          <div class="director-info">
            <div class="list-item_title">Delivery Address</div>
            <div class="list-item__subtitle">
              <ul class="address-details">
                <li>{{ director.deliveryAddress.streetAddress }}</li>
                <li>{{ director.deliveryAddress.addressCity }} {{ director.deliveryAddress.addressRegion }}
                  {{ director.deliveryAddress.postalCode}}</li>
                <li>{{ director.deliveryAddress.addressCountry }}</li>
              </ul>
            </div>
          </div>
        </li>
        <li class="list-item" v-if="entityFilter(EntityTypes.BCorp)">
          <div class="director-info">
            <div class="list-item_title">Mailing Address</div>
            <div class="list-item__subtitle">
              <span v-if="isSameAddress(director.deliveryAddress.streetAddress, director.mailingAddress.streetAddress)">
                Same as above
              </span>
              <ul v-else class="address-details" >
                <li>{{ director.mailingAddress.streetAddress }}</li>
                <li>{{ director.mailingAddress.addressCity }} {{ director.mailingAddress.addressRegion }}
                  &nbsp;&nbsp;{{ director.mailingAddress.postalCode}}</li>
                <li>{{ director.mailingAddress.addressCountry }}</li>
              </ul>
            </div>
          </div>
        </li>
      </v-expansion-panel-content>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script lang="ts">

// Vue Libraries
import { Component } from 'vue-property-decorator'
import { mixins } from 'vue-class-component'
import { mapState } from 'vuex'

// Mixins
import { EntityFilterMixin, AddressMixin } from '@/mixins'

// Constants
import { EntityTypes } from '@/enums'

@Component({
  computed: {
    ...mapState(['directors'])
  }
})
export default class DirectorListSm extends mixins(EntityFilterMixin, AddressMixin) {
  readonly directors: Array<object>

  // EntityTypes Enum
  readonly EntityTypes: {} = EntityTypes
}
</script>

<style lang="scss" scoped>

  .list-container {
    padding: 0 .3rem
  }

  .v-expansion-panel-header {
    padding: 1rem 1rem;
  }

  .v-avatar {
    flex: 0 0 auto;
    color: #fff7e3;
    margin-right: 1.25rem
  }
  .v-expansion-panel-header__icon{
    color: #262626;
  }

  .list-container-content{
    padding: 0 2.75rem;
  }

  .address-details {
    padding: 0;
    list-style-type: none
  }

  .list-item {
    padding: .5rem 1.25rem;
    flex-direction: row;
    align-items: center;
    background: #ffffff;

    .list-item_title {
      padding-bottom: .5rem
    }
  }

  .list-item + .list-item {
    border-top: none
  }

</style>
