<template>
  <ul class="list">
    <li class="list-item">
      {{ mailingAddress.street }}
      {{ mailingAddress.city }}
      {{ mailingAddress.country }}
      {{ mailingAddress.region }}
    </li>
    <li class="list-item">
      {{ deliveryAddress.street }}
      {{ deliveryAddress.city }}
      {{ deliveryAddress.country }}
      {{ deliveryAddress.region }}
    </li>
  </ul>
</template>

<script>
export default {
  name: 'AddressListSm',

  data () {
    return {
      mailingAddress: {
        street: '1234 Main Street',
        city: 'Victoria',
        country: 'Canada',
        region: 'BC'
      },
      deliveryAddress: {
        inherit: false,
        street: '1234 Main Street',
        city: 'Victoria',
        country: 'Canada',
        region: 'BC'
      }
    }
  }
}
</script>

<style lang="stylus" scoped>
  ul
    list-style-type none
</style>
