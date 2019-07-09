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
  .list .list-item
    flex-directon column
</style>
