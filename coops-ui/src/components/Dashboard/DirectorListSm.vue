<template>
  <ul class="list list-container">
    <li class="list-item" v-for="director in directors" v-bind:key="director.id">
      <v-avatar color="primary" size="25">
        <span class="white--text small">{{ director.officer.firstName.substring(0,1)}}</span>
      </v-avatar>
      <div class="director-info">
        <div class="list-item__title">{{ director.officer.firstName }} {{ director.officer.lastName }}</div>
        <div class="list-item__subtitle">
          <ul class="address-details">
            <li>{{ director.deliveryAddress.streetAddress }}</li>
            <li>{{ director.deliveryAddress.addressCity }} {{ director.deliveryAddress.addressRegion }}
              &nbsp;&nbsp;{{ director.postalCode}}</li>
            <li>{{ director.deliveryAddress.addressCountry }}</li>
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
    ...mapState(['directors'])
  }
})
export default class DirectorListSm extends Vue {
  readonly directors: Array<object>
}
</script>

<style lang="scss" scoped>
  .address-details {
    padding: 0;
    list-style-type: none
  }

  .list-item {
    flex-direction: row;
    align-items: center;
    background: #ffffff;
  }

  .v-icon {
    margin-right: 1rem;
  }

  .v-avatar {
    flex: 0 0 auto;
    margin-right: 1.25rem
  }

  .card {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .card .list-item {
    flex: 0 0 33.333333%;
    border: none;
  }

  .list-container {
   padding-left:0
  }
</style>
