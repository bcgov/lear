<template>
  <ul class="list list-container">
    <li class="list-item" v-if="mailingAddress">
      <v-avatar>
        <v-icon color="primary">mdi-email-outline</v-icon>
      </v-avatar>
      <div class="address">
        <div class="list-item__title">Mailing Address</div>
        <div class="list-item__subtitle">
          <ul class="address-details">
            <li>{{ mailingAddress.streetAddress }}</li>
            <li>{{ mailingAddress.addressCity }} {{ mailingAddress.addressRegion }}
              &nbsp;&nbsp;{{ mailingAddress.postalCode}}</li>
            <li>{{ mailingAddress.addressCountry }}</li>
          </ul>
        </div>
      </div>
    </li>

    <li class="list-item" v-if="deliveryAddress">
      <v-avatar>
        <v-icon color="primary">mdi-truck</v-icon>
      </v-avatar>
      <div class="address">
        <div class="list-item__title">Delivery Address</div>
        <div class="list-item__subtitle">
          <ul class="address-details">
            <li>{{ deliveryAddress.streetAddress }}</li>
            <li>{{ deliveryAddress.addressCity }} {{ deliveryAddress.addressRegion }}
              &nbsp;&nbsp;{{ deliveryAddress.postalCode}}</li>
            <li>{{ deliveryAddress.addressCountry }}</li>
          </ul>
        </div>
      </div>
    </li>
  </ul>
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
  .address-details{
    padding: 0;
    list-style-type: none
  }

  .list-container{
   padding-left:0
  }

  .list-item{
    flex-direction: row;
    align-items: flex-start
  }

  .v-icon{
    margin-right: 1.25rem
  }
</style>
