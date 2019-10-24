<template>
  <v-list>
    <v-list-item v-if="mailingAddress">
      <v-list-item-icon class="address-icon mr-0">
        <v-icon color="primary">mdi-email-outline</v-icon>
      </v-list-item-icon>
      <v-list-item-content>
        <v-list-item-title class="mb-2">Mailing Address</v-list-item-title>
        <v-list-item-subtitle>
          <ul class="address-info">
            <li>{{ mailingAddress.streetAddress }}</li>
            <li>{{ mailingAddress.addressCity }} {{ mailingAddress.addressRegion }}
              &nbsp;&nbsp;{{ mailingAddress.postalCode}}</li>
            <li>{{ mailingAddress.addressCountry }}</li>
          </ul>
        </v-list-item-subtitle>
      </v-list-item-content>
    </v-list-item>

    <v-divider></v-divider>

    <v-list-item v-if="deliveryAddress">
      <v-list-item-icon class="address-icon mr-0">
        <v-icon color="primary">mdi-truck</v-icon>
      </v-list-item-icon>
      <v-list-item-content>
        <v-list-item-title class="mb-2">Delivery Address</v-list-item-title>
        <v-list-item-subtitle>
          <ul class="address-info">
            <li>{{ deliveryAddress.streetAddress }}</li>
            <li>{{ deliveryAddress.addressCity }} {{ deliveryAddress.addressRegion }}
              &nbsp;&nbsp;{{ deliveryAddress.postalCode}}</li>
            <li>{{ deliveryAddress.addressCountry }}</li>
          </ul>
        </v-list-item-subtitle>
      </v-list-item-content>
    </v-list-item>
  </v-list>

</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { mapState } from 'vuex'

@Component({
  computed: {
    ...mapState(['mailingAddress', 'deliveryAddress'])
  }
})
export default class AddressListSm extends Vue {
  readonly mailingAddress: object
  readonly deliveryAddress: object
}
</script>

<style lang="scss" scoped>
  @import "../../assets/styles/theme.scss";

  // Variables
  $icon-width: 2.75rem;

  .v-list-item__icon {
    margin-top: 0.7rem;
    margin-right: 0;
  }

  .v-list-item__title {
    font-size: 0.875rem;
    font-weight: 700;
  }

  .v-divider {
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .address-icon {
    width: $icon-width;
  }

  .address-info {
    margin: 0;
    padding: 0;
    list-style-type: none;
  }
</style>
