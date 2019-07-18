<template>
  <div v-if="taskItems">
    <v-card flat>
      <ul class="list todo-list">
        <li class="list-item" v-for="(item, index) in taskItems" v-bind:key="index" :class="{ 'disabled': !item.enabled }">
          <div class="list-item__title">{{item.title}}</div>

          <div class="list-item__subtitle" v-if="isNew(item)">
            <span v-if="item.subtitle">{{item.subtitle}}</span>
          </div>
          <template v-else>
            <div class="list-item__status1">
              <span v-if="isDraft(item)">DRAFT</span>
              <span v-else-if="isPending(item)">FILING PENDING</span>
              <span v-else-if="isError(item)">FILING PENDING</span>
            </div>

            <div class="list-item__status2">
              <span v-if="isPending(item)">
                PAYMENT INCOMPLETE<v-btn flat icon color="black"><v-icon>info_outline</v-icon></v-btn>
              </span>
              <span v-else-if="isError(item)">
                PAYMENT UNSUCCESSFUL<v-btn flat icon color="black"><v-icon>info_outline</v-icon></v-btn>
              </span>
            </div>
          </template>

          <div class="list-item__actions">
            <v-btn color="primary" v-if="isDraft(item)" :disabled="!item.enabled" @click="doResumeFiling(item)">
              Resume
            </v-btn>
            <v-btn color="primary" v-else-if="isPending(item)" :disabled="!item.enabled" @click="doResumePayment(item)">
              Resume Payment
            </v-btn>
            <v-btn color="primary" v-else-if="isError(item)" :disabled="!item.enabled" @click="doRetryPayment(item)">
              Retry Payment
            </v-btn>
            <v-btn color="primary" v-else-if="!isCompleted(item)" :disabled="!item.enabled" @click="doFileNow(item)">
              File Now
            </v-btn>
          </div>
        </li>
      </ul>
    </v-card>

    <!-- No Results Message -->
    <v-card class="no-results" flat v-if="taskItems.length === 0 && !errorMessage">
      <v-card-text>
        <div class="no-results__title">You don't have anything to do yet</div>
        <div class="no-results__subtitle">Filings that require your attention will appear here</div>
      </v-card-text>
    </v-card>

    <!-- Error Message -->
    <v-card class="network-error" flat v-if="taskItems.length === 0 && errorMessage">
      <v-card-text>
        <div class="network-error__title">{{errorMessage}}</div>
        <div class="network-error__subtitle">Filings that require your attention will normally appear here</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import Vue2Filters from 'vue2-filters'
import axios from '@/axios-auth'
import { mapState, mapActions } from 'vuex'
import sample from './tasks_json' // FOR DEBUGGING

export default {
  name: 'TodoList',

  mixins: [Vue2Filters.mixin],

  data () {
    return {
      taskItems: null,
      errorMessage: null
    }
  },

  computed: {
    ...mapState(['corpNum']),

    // TODO - implement Filing Unavailable functionality (ticket #920)
    isFilingUnavailable () {
      // const openHours = [
      //   {
      //     "Monday to Friday": { from: 600, to: 2100 },
      //     "Saturday": { from: 0, to: 700 },
      //     "Sunday": { from: 1200, to: 0 }
      //   }
      // ]
      return false
    }
  },

  mounted () {
    // reload data for this page
    this.getTasks()
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setCurrentARStatus', 'setRegOffAddrChange', 'setAgmDate',
      'setFiledDate', 'setNoAGM', 'setValidated']),

    getTasks () {
      this.taskItems = []
      this.errorMessage = null
      if (this.corpNum) {
        // const url = this.corpNum + '/tasks'
        // axios.get(url).then(response => {
          const response = { data: { tasks: sample.tasks }} // FOR DEBUGGING
          if (response && response.data && response.data.tasks) {
            // sort by id ascending
            const tasks = response.data.tasks.sort((a, b) => (a.order - b.order))
            // create items
            tasks.forEach(task => {
              if (task.todo) {
                this.loadTodoItem(task)
              } else if (task.filing) {
                this.loadFilingItem(task)
              } else {
                console.log('ERROR - got unknown task =', task)
              }
            })
          } else {
            console.log('getTasks() error - invalid Filings')
            this.errorMessage = 'Oops, could not parse data from server'
          }
          this.$emit('todo-count', this.taskItems.length)
        // }).catch(error => {
        //   console.error('getTasks() error =', error)
        //   this.errorMessage = 'Oops, could not load data from server'
        // })
      }
    },

    loadTodoItem (task) {
      if (task.todo && task.todo.header) {
        switch (task.todo.header.name) {
          case 'annual_report': {
            const ARFilingYear = task.todo.header.ARFilingYear
            this.taskItems.push({
              type: task.todo.header.name,
              title: `File ${ARFilingYear} Annual Report`,
              subtitle: task.enabled ? '(including Address and/or Director Change)' : null,
              ARFilingYear,
              status: task.todo.header.status || 'NEW',
              enabled: Boolean(task.enabled)
            })
            break
          }
          default:
            console.log('ERROR - got unknown todo item =', task)
            break
        }
      }
    },

    loadFilingItem (task) {
      if (task.filing && task.filing.header) {
        switch (task.filing.header.name) {
          case 'annual_report':
            this.loadAnnualReport(task)
            break
          case 'change_of_directors':
            this.loadChangeOfDirectors(task)
            break
          case 'change_of_address':
            this.loadChangeOfAddress(task)
            break
          default:
            console.log('ERROR - got unknown filing =', task.filing)
            break
        }
      }
    },

    loadAnnualReport (task) {
      if (task.filing && task.filing.header && task.filing.annualReport) {
        const date = task.filing.annualReport.annualGeneralMeetingDate
        if (date) {
          const ARFilingYear = +date.substring(0, 4)
          this.taskItems.push({
            type: task.filing.header.name,
            title: `File ${ARFilingYear} Annual Report`,
            ARFilingYear,
            status: task.filing.header.status || 'NEW',
            enabled: Boolean(task.enabled)
          })
        }
      }
    },

    loadChangeOfDirectors (task) {
      if (task.filing && task.filing.header && task.filing.changeOfDirectors) {
        this.taskItems.push({
          type: task.filing.header.name,
          title: `File Director Change`,
          status: task.filing.header.status || 'NEW',
          enabled: Boolean(task.enabled)
        })
      }
    },

    loadChangeOfAddress (task) {
      if (task.filing && task.filing.header && task.filing.changeOfAddress) {
        this.taskItems.push({
          type: task.filing.header.name,
          title: `File Address Change`,
          status: task.filing.header.status || 'NEW',
          enabled: Boolean(task.enabled)
        })
      }
    },

    doFileNow (item) {
      switch (item.type) {
        case 'annual_report':
          // file the subject Annual Report
          this.resetStore(item)
          this.$router.push('/annual-report')
          break
        case 'change_of_directors':
          // TODO - file the subject Change of Directors
          console.log('doFileNow(), Director Change item =', item)
          break
        case 'change_of_address':
          // TODO - file the subject Change Of Address
          console.log('doFileNow(), Address Change item =', item)
          break
        default:
          console.log('doFileNow(), invalid type for item =', item)
      }
    },

    doResumeFiling (item) {
      // TODO
      this.doFileNow(item) // for now...
    },

    doResumePayment (item) {
      // TODO
    },

    doPay (item) {
      // TODO
    },

    doRetryPayment (item) {
      // TODO
    },

    resetStore (item) {
      this.setARFilingYear(item.ARFilingYear)
      this.setCurrentARStatus('TODO')
      this.setRegOffAddrChange(false)
      this.setAgmDate(null)
      this.setFiledDate(null)
      this.setNoAGM(false)
      this.setValidated(false)
    },

    isNew (item) {
      return item.status === 'NEW'
    },

    isDraft (item) {
      return item.status === 'DRAFT'
    },

    isPending (item) {
      return item.status === 'PENDING'
    },

    isError (item) {
      return item.status === 'ERROR'
    },

    isCompleted (item) {
      return item.status === 'COMPLETED'
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new task items
      this.getTasks()
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"

  .list-item
    .list-item__title
      width 25%

    .list-item__subtitle
      font-size 0.75rem

    .list-item__status1
      width 20%
      color $gray7

    .list-item__status2
      width 36%
      color $gray7

      .v-btn
        margin 0

    .list-item__actions
      .v-btn
        min-width 142px

  .list-item.disabled
    background-color $gray0

    .list-item__title,
    .list-item__subtitle,
    .list-item__status1,
    .list-item__status2
      color $gray6
</style>
