<template>
  <ul class="list">
    <li class="list-item" v-for="director in directors" v-bind:key="director.id">
      <div class="list-item-title">{{ director.officer.firstName }} {{ director.officer.lastName }}</div>
      <!-- <div class="list-item-subtitle">MMM DD, YYYY</div> -->
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
        // TODO - make proper axios call and delete hardcoded data below
        // const url = this.corpNum + '/directors'
        // axios.get(url).then(response => {
        //   if (response && response.data && response.data.directors) {
        //     this.directors = response.data.directors
        //     for (var i = 0; i < this.directors.length; i++) {
        //       this.directors[i].id = i + 1
        //       this.directors[i].isNew = false
        //       this.directors[i].isDirectorActive = true
        //     }
        //   } else {
        //     console.log('getDirectors() error - invalid Directors')
        //   }
        // }).catch(error => console.error('getDirectors() error =', error))
        this.directors = [
          {
            id: 1,
            isNew: false,
            isDirectorActive: true,
            officer: { firstName: 'Alli', lastName: 'Myers', middleInitial: '' },
            deliveryAddress: {
              streetAddress: '1111 First Street',
              streetAddressAdditional: '',
              addressCity: 'Victoria',
              addressRegion: 'BC',
              postalCode: 'V8A 2G8',
              addressCountry: 'Canada'
            },
            title: 'Pres'
          },
          {
            id: 2,
            isNew: false,
            isDirectorActive: true,
            officer: { firstName: 'Nora', lastName: 'Patton', middleInitial: '' },
            deliveryAddress: {
              streetAddress: '2222 Second Street',
              streetAddressAdditional: '',
              addressCity: 'Victoria',
              addressRegion: 'BC',
              postalCode: 'V8A 2G8',
              addressCountry: 'Canada'
            },
            title: null
          },
          {
            id: 3,
            isNew: false,
            isDirectorActive: true,
            officer: { firstName: 'Phoebe', lastName: 'Jones', middleInitial: '' },
            deliveryAddress: {
              streetAddress: '3333 Third Street',
              streetAddressAdditional: null,
              addressCity: 'Victoria',
              addressRegion: 'BC',
              postalCode: 'V8A 2G8',
              addressCountry: 'Canada'
            },
            title: null
          },
          {
            id: 4,
            isNew: false,
            isDirectorActive: true,
            officer: { firstName: 'Cole', lastName: 'Bryan', middleInitial: '' },
            deliveryAddress: {
              streetAddress: '4444 Fourth Street',
              streetAddressAdditional: null,
              addressCity: 'Victoria',
              addressRegion: 'BC',
              postalCode: 'V8A 2G8',
              addressCountry: 'Canada'
            },
            title: 'Vice Pres'
          }
        ]
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
  .list .list-item
    flex-directon column
</style>
