<template>
  <div id="dashboard">

    <!-- Initial Page Load Transition -->
    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
        <div class="loading-msg">Loading Your Dashboard</div>
      </div>
    </div>

    <v-container id="dashboardContainer" class="view-container">
      <article id="dashboardArticle">
        <header>
          <h1 id="dashboardHeader">Dashboard</h1>
        </header>

        <v-btn id="go-to-ar-btn" large to="/annual-report" :disabled="!ARFilingYear">
        File Annual Report</v-btn>

        <section>
          <header>
            <h2 id="dashboardTodoHeader">To Do
              <span class="text-muted" v-if="todoItems">({{todoItems.length}})</span></h2>
          </header>
          <v-card flat id="dashboardTodoContainer">
            <!-- TODO -->
          </v-card>
        </section>

        <section>
          <header>
            <h2 id="dashboardFilingHeader">Recent Filing History
              <span class="text-muted" v-if="filedItems">({{filedItems.length}})</span></h2>
          </header>
          <v-card flat id="dashboardFilingContainer">
            <!-- TODO -->
          </v-card>
        </section>
      </article>
    </v-container>

  </div>
</template>

<script lang="ts">
import axios from '@/axios-auth'
// TODO - implement these
// import TodoList from '@/components/TodoList.vue'
// import FilingHistory from '@/components/FilingHistory.vue'

export default {
  name: 'Dashboard',

  components: {
    // TodoList,
    // FilingHistory
  },

  data () {
    return {
      todoItems: null,
      filedItems: null
    }
  },

  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
    currentDate () {
      return this.$store.state.currentDate
    },
    lastAgmDate () {
      return this.$store.state.lastAgmDate
    },
    ARFilingYear () {
      return this.$store.state.ARFilingYear
    }
  },

  mounted () {
    console.log('Dashboard is mounted')
  },

  methods: {
    getTodoItems () {
      if (!this.corpNum) {
        console.log('getTodoItems() error - Corp Num is null')
      } else {
        // TODO - make proper axios call
        var url = this.corpNum + '/todo'
        axios.get(url).then(response => {
          if (response && response.data) {
            this.todoItems = response.data
          } else {
            console.log('getTodoItems() error - invalid response data')
          }
        }).catch(error => {
          console.error('getTodoItems() error =', error)

          // TODO - delete this when API works
          this.todoItems = [
            { name: 'File 2018 Annual Report', enabled: true },
            { name: 'File 2019 Annual Report', enabled: true }
          ]
        })
      }
    },
    getFiledItems () {
      if (!this.corpNum) {
        console.log('getFiledItems() error - Corp Num is null')
      } else {
        // TODO - make proper axios call
        var url = this.corpNum + '/filingsx'
        axios.get(url).then(response => {
          if (response && response.data) {
            this.filedItems = response.data
          } else {
            console.log('getFiledItems() error - invalid response data')
          }
        }).catch(error => {
          console.error('getFiledItems() error =', error)

          // TODO - delete this when API works
          this.filedItems = [
            {
              name: 'Annual Report (2017)',
              filingAuthor: 'Jane Doe',
              filingDate: 'Feb 01, 2018',
              filingStatus: 'Complete',
              filingDocuments: [
                { name: 'Change of Address' },
                { name: 'Change of Directors' },
                { name: 'Annual Report' }
              ]
            },
            {
              name: 'Annual Report (2016)',
              filingAuthor: 'Jane Doe',
              filingDate: 'Feb 05, 2017',
              filingStatus: 'Complete',
              filingDocuments: [
                { name: 'Change of Address' },
                { name: 'Change of Directors' },
                { name: 'Annual Report' }
              ]
            },
            {
              name: 'Annual Report (2015)',
              filingAuthor: 'Jane Doe',
              filingDate: 'Feb 07, 2016',
              filingStatus: 'Complete',
              filingDocuments: [
                { name: 'Change of Address' },
                { name: 'Change of Directors' },
                { name: 'Annual Report' }
              ]
            }
          ]
        })
      }
    },
    setARInfo () {
      // console.log('setARInfo, lastAgmDate =', this.lastAgmDate)
      if (this.currentDate && this.lastAgmDate) {
        const currentYear = +this.currentDate.substring(0, 4)
        const lastAgmYear = +this.lastAgmDate.substring(0, 4)
        if (lastAgmYear < currentYear) {
          this.$store.state.ARFilingYear = (lastAgmYear + 1).toString()
        } else {
          // already filed for this year
          this.$store.state.ARFilingYear = null
        }
      }
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new items
      this.getTodoItems()
      this.getFiledItems()
    },
    lastAgmDate (val) {
      // when Last AGM Date is set or changes, set AR info
      this.setARInfo()
    }
    // TODO - need to watch something to update dashboard after new AR is submitted
  }
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  // TODO: Create/Move to Helper Stylesheet
  .text-muted
    color $gray5

  article
    .v-card
      line-height 1.2rem
      font-size 0.875rem

  section p
    //font-size 0.875rem
    color $gray6

  section + section
    margin-top 3rem

  h2
    margin-bottom 0.25rem

  #dashboardHeader
    margin-bottom 1.25rem
    line-height 2rem
    letter-spacing -0.01rem
    font-size 2rem
    font-weight 500

  #dashboardTodoHeader, #dashboardFilingHeader
    margin-bottom 0.25rem
    margin-top 3rem
    font-size 1.125rem
    font-weight 500

  #dashboardTodoContainer, #dashboardFilingContainer
    margin-top 1rem
</style>
