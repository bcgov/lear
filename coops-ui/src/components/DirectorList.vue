<template>
  <ul class="director-list">
    <li class="container" v-for="director in directors" v-bind:key="director.id">
      <label class="director__name">
        <span>{{director.firstName}}</span><span>&nbsp;{{director.lastName}}</span>
      </label>
      <div class="value">
        <div class="address-block__row">{{director.street}}</div>
        <div class="address-block__row">
          <span>{{director.city}}</span>
          <span>&nbsp;{{director.province}}</span>
          <span>&nbsp;&nbsp;{{director.postalCode}}</span>
        </div>
        <div class="address-block__row">{{director.country}}</div>
      </div>
      <div class="actions">
        <v-btn small outline color="blue">Edit</v-btn>
      </div>
    </li>
  </ul>
</template>

<script>
export default {
  name: 'DirectorList',

  data: () => ({
    directors: [
      {firstName: "Jane", lastName: "Doe", street: "1234 Main Street", city: "Victoria", province: "BC", postalCode: "V8A 2G8", country: "Canada"},
      {firstName: "John", lastName: "Doe", street: "1234 Main Street", city: "Victoria", province: "BC", postalCode: "V8A 2G8", country: "Canada"},
      {firstName: "Jane", lastName: "Doe", street: "1234 Main Street", city: "Victoria", province: "BC", postalCode: "V8A 2G8", country: "Canada"},
      {firstName: "John", lastName: "Doe", street: "1234 Main Street", city: "Victoria", province: "BC", postalCode: "V8A 2G8", country: "Canada"}
    ]
  })
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

</style>