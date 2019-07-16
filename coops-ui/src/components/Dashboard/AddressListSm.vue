<template>
  <ul class="list">
    <li class="list-item" v-if="mailingAddress">
      <v-avatar>
        <v-icon color="primary">mail_outline</v-icon>
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
        <v-icon color="primary">local_shipping</v-icon>
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

<script>
import axios from '@/axios-auth'
import { mapState } from 'vuex'

export default {
  name: 'AddressListSm',

  data () {
    return {
      mailingAddress: null,
      deliveryAddress: null
    }
  },

  computed: {
    ...mapState(['corpNum'])
  },

  mounted () {
    // reload data for this page
    this.getAddresses()
  },

  methods: {
    getAddresses () {
      if (this.corpNum) {
        const url = this.corpNum + '/addresses'
        axios.get(url).then(response => {
          if (response && response.data && response.data.mailingAddress) {
            this.mailingAddress = response.data.mailingAddress
          } else {
            console.log('getAddresses() error - invalid Mailing Address')
          }
          if (response && response.data && response.data.deliveryAddress) {
            this.deliveryAddress = response.data.deliveryAddress
          } else {
            console.log('getAddresses() error - invalid Delivery Address')
          }
        }).catch(error => console.error('getAddresses() error =', error))
      }
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new addresses
      this.getAddresses()
    }
  }
}
</script>

<style lang="stylus" scoped>
  .address-details
    padding 0
    list-style-type none

  .list-item
    flex-direction row
    align-items flex-start

  .v-icon
    margin-right 1.25rem
</style>
