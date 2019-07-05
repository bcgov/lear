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

        <section v-if="todoItems && todoItems.length">
          <header>
            <h2 id="dashboardTodoHeader">To Do
              <span class="text-muted">({{todoItems.length}})</span>
            </h2>
          </header>

          <v-card flat id="dashboardTodoContainer">
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
        </section>

        <section v-if="filedItems && filedItems.length">
          <header>
            <h2 id="dashboardFilingHeader">Recent Filing History
              <span class="text-muted">({{filedItems.length}})</span>
            </h2>
          </header>

          <v-card flat id="dashboardFilingContainer">
            <v-expansion-panel>
              <v-expansion-panel-content
                class="filing-history-list"
                v-for="(item, index) in orderBy(filedItems, 'name', -1)"
                v-bind:key="index">
                <template v-slot:header>
                  <div class="list-item">
                    <div class="list-item-title">{{item.name}}</div>
                    <div class="list-item-subtitle">Filed by {{item.filingAuthor}} on {{item.filingDate}}</div>
                  </div>
                </template>

                <ul class="list document-list">
                  <li class="list-item"
                    v-for="(document, index) in orderBy(item.filingDocuments, 'name')"
                    v-bind:key="index">
                    <a href="#">
                      <img class="list-item-icon" src="@/assets/images/icons/file-pdf-outline.svg" />
                      <div class="list-item-title">{{document.name}}</div>
                    </a>
                  </li>
                  <li class="list-item">
                    <a href="#">
                      <img class="list-item-icon" src="@/assets/images/icons/file-pdf-outline.svg" />
                      <div class="list-item-title">Receipt</div>
                    </a>
                  </li>
                </ul>
                <div class="documents-actions-bar">
                  <v-btn class="download-all-btn" color="primary" @click="downloadAll(item)">Download All</v-btn>
                </div>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-card>
        </section>
      </article>
    </v-container>

  </div>
</template>

<script lang="ts">
import { Vue } from 'vue-property-decorator'
import Vue2Filters from 'vue2-filters'
import axios from '@/axios-auth'
// TODO - implement these
// import TodoList from '@/components/TodoList.vue'
// import FilingHistory from '@/components/FilingHistory.vue'

Vue.use(Vue2Filters)

export default {
  name: 'Dashboard',

  mixins: [Vue2Filters.mixin],

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
    this.getTodoItems()
    this.getFiledItems()
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
      }
    },
    getFiledItems () {
      if (this.corpNum) {
        // TODO - make proper axios call
        var url = this.corpNum + '/filings'
        axios.get(url).then(response => {
          if (response && response.data) {
            // this.filedItems = response.data
            // TODO - build actual data from response
            this.filedItems = [
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
                name: 'Annual Report (2017)',
                filingAuthor: 'Jane Doe',
                filingDate: 'Feb 01, 2018',
                filingStatus: 'Complete',
                filingDocuments: [
                  { name: 'Change of Address' },
                  { name: 'Change of Directors' },
                  { name: 'Annual Report' }
                ]
              }
            ]
          } else {
            console.log('getFiledItems() error - invalid response data')
          }
        }).catch(error => console.error('getFiledItems() error =', error))
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
    },
    fileAnnualReport (item) {
      console.log('fileAnnualReport(), item =', item)
      this.$router.push({ path: '/annual-report', query: { year: item.year } })
    },
    downloadAll (item) {
      console.log('downloadAll(), item =', item)
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num changes, get new items
      this.getTodoItems()
      this.getFiledItems()
    },
    lastAgmDate (val) {
      // when Last AGM Date changes, set AR info
      this.setARInfo()
    }
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

  // Common
  .list
    margin 0
    padding 0
    list-style-type none

  .list-item
    display flex
    flex-direction row
    align-items center
    padding 1.25rem
    background #fff
    font-size 0.875rem

  list-item + .list-item
    border-top 1px solid $gray3

  .list-item-icon
    margin-top -1px
    margin-right 0.5rem
    opacity 0.4

  .list-item-title
    font-weight 700

  .list-item-subtitle
    color $gray5
    font-weight 400

  .list-item-actions
    flex 0 0 auto
    margin-left auto

    .v-btn
      margin 0
      min-width 8rem
      font-weight 500

  // Filing History
  .filing-history-list .list-item
    flex-direction column
    align-items flex-start
    padding 0

  // Document List
  .document-list
    border-top 1px solid $gray3

    .list-item a
      display flex
      flex-direction row
      align-items center
      padding 0.5rem

    .list-item-title
      font-weight 400

  // Documents Action Bar
  .documents-actions-bar
    padding-top 1rem
    padding-bottom 1.25rem
    display flex
    border-top 1px solid $gray3

    .v-btn
      margin-right 0

  .download-all-btn
    margin-left auto
    min-width 8rem
</style>
