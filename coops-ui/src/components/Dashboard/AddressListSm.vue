<template>
  <ul class="list">
    <li class="list-item" v-if="mailingAddress">
      {{ mailingAddress.streetAddress }}<br>
      {{ mailingAddress.addressCity }}, {{ mailingAddress.addressRegion }}<br>
      {{ mailingAddress.addressCountry }}
    </li>
    <li class="list-item" v-if="deliveryAddress">
      {{ deliveryAddress.streetAddress }}<br>
      {{ deliveryAddress.addressCity }}, {{ deliveryAddress.addressRegion }}<br>
      {{ deliveryAddress.addressCountry }}
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
  ul
    list-style-type none
</style>
