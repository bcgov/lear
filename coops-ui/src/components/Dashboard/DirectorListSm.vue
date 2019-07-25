<template>
  <ul class="list">
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

<script>
import axios from '@/axios-auth'
import { mapState } from 'vuex'

export default {
  name: 'DirectorListSm',

  data () {
    return {
      directors: null
    }
  },

  computed: {
    ...mapState(['corpNum'])
  },

  mounted () {
    // reload data for this page
    this.getDirectors()
  },

  methods: {
    getDirectors () {
      if (this.corpNum) {
        var url = this.corpNum + '/directors'
        axios.get(url).then(response => {
          if (response && response.data && response.data.directors) {
            this.directors = response.data.directors
            for (var i = 0; i < this.directors.length; i++) {
              this.directors[i].id = i + 1
              this.directors[i].isNew = false
              this.directors[i].isDirectorActive = true
            }
          } else {
            console.log('getDirectors() error - invalid Directors')
          }
        }).catch(error => console.error('getDirectors() error =', error))
      }
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new directors
      this.getDirectors()
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
    align-items center
    background #ffffff

  .v-icon
    margin-right 1rem

  .v-avatar
    flex 0 0 auto
    margin-right 1.25rem

  .card
    display flex
    flex-wrap wrap
    align-items flex-start

  .card .list-item
    flex 0 0 33.333333%
    border none
</style>
