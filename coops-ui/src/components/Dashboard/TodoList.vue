<template>
  <div v-if="todoItems">
    <v-card flat>
      <ul class="list todo-list">
        <li class="list-item"
          v-for="(item, index) in orderBy(todoItems, 'year', 1)"
          v-bind:key="index">
          <div class="list-item-title">{{item.name}}</div>
          <div class="list-item-actions">
            <v-btn color="primary" @click="fileAnnualReport(item)" :disabled="!item.enabled">File Now</v-btn>
          </div>
        </li>
      </ul>
    </v-card>

     <!-- No Results Message -->
    <v-card class="no-results" flat v-if="todoItems.length === 0">
      <v-card-text>
        <div class="no-results__title">You don't have anything to do yet</div>
        <div class="no-results__subtitle">Filings that require your attention will appear here</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import Vue2Filters from 'vue2-filters'

export default {
  name: 'TodoList',

  mixins: [Vue2Filters.mixin],

  data () {
    return {
      todoItems: null
    }
  },

  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
    currentDate () {
      return this.$store.state.currentDate
    }
  },

  mounted () {
    // reload data for this page
    this.getTodoItems()
  },

  methods: {
    getTodoItems () {
      // TODO - this needs to be constructed based on last AR date (not retrieved)
      // only the earliest non-submitted AR can be filed
      if (this.corpNum) {
        this.todoItems = [
          { name: 'File 2019 Annual Report', year: 2019, enabled: false },
          { name: 'File 2018 Annual Report', year: 2018, enabled: true }
        ]
        this.$emit('todo-count', this.todoItems.length)
      }
    },
    fileAnnualReport (item) {
      // console.log('fileAnnualReport(), item =', item)
      this.$router.push({ path: '/annual-report', query: { year: item.year } })
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new todo items
      this.getTodoItems()
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"
</style>
