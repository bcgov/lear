<template>
  <div id="dashboard">
    <v-container id="dashboardContainer" class="view-container">
      <article id="dashboardArticle">
        <header>
          <h1>Dashboard</h1>
        </header>

        <div class="dashboard-content">
          <div class="dashboard-content__main">
            <section>
              <header>
                <h2 class="mb-3">To Do <span class="text-muted">({{todoCount}})</span></h2>
              </header>
              <todo-list @todo-count="todoCount = $event" @has-blocker-filing="hasBlockerFiling = $event"
                         @todo-filings="todoListFilings = $event" :inProcessFiling="inProcessFiling" />
            </section>
            <section>
              <header>
                <h2 class="mb-3">Recent Filing History <span class="text-muted">({{filedCount}})</span></h2>
              </header>
              <filing-history-list @filed-count="filedCount = $event" @filings-list="historyFilings = $event" />
            </section>
          </div>

          <aside class="dashboard-content__aside">
            <section>
              <header class="aside-header mb-3">
                <h2>Office Addresses</h2>
                <v-btn text small color="primary" id="btn-standalone-addresses" :disabled="hasBlockerFiling"
                      @click.native.stop="goToStandaloneAddresses()">
                  <v-icon small>mdi-pencil</v-icon>
                  <span>Change</span>
                </v-btn>
              </header>
              <v-card flat>
                <address-list-sm></address-list-sm>
              </v-card>
            </section>

            <section>
              <header class="aside-header mb-3">
                <h2>Current Directors</h2>
                <v-btn text small color="primary" id="btn-standalone-directors" :disabled="hasBlockerFiling"
                      @click.native.stop="goToStandaloneDirectors()">
                  <v-icon small>mdi-pencil</v-icon>
                  <span>Change</span>
                </v-btn>
              </header>
              <v-card flat>
                <director-list-sm></director-list-sm>
              </v-card>
            </section>
          </aside>
        </div>
      </article>
    </v-container>
  </div>
</template>

<script>
import axios from '@/axios-auth'
import TodoList from '@/components/Dashboard/TodoList.vue'
import FilingHistoryList from '@/components/Dashboard/FilingHistoryList.vue'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'
import DirectorListSm from '@/components/Dashboard/DirectorListSm.vue'
import { mapState, mapActions } from 'vuex'
import { withFlags } from 'ld-vue'

export default {
  name: 'Dashboard',

  mixins: [withFlags],

  components: {
    TodoList,
    FilingHistoryList,
    AddressListSm,
    DirectorListSm
  },

  data () {
    return {
      todoCount: 0,
      hasBlockerFiling: false,
      filedCount: 0,
      historyFilings: [],
      todoListFilings: [],
      refreshTimer: null,
      checkFilingStatusCount: 0,
      inProcessFiling: null
    }
  },

  computed: {
    ...mapState(['entityIncNo'])
  },

  methods: {
    ...mapActions(['setCurrentFilingStatus', 'setTriggerDashboardReload']),

    goToStandaloneDirectors () {
      this.setCurrentFilingStatus('NEW')
      this.$router.push({ name: 'standalone-directors', params: { id: 0 } }) // 0 means "new COD filing"
    },

    goToStandaloneAddresses () {
      this.setCurrentFilingStatus('NEW')
      this.$router.push({ name: 'standalone-addresses', params: { id: 0 } }) // 0 means "new COA filing"
    },

    checkToReloadDashboard () {
      // cancel any existing timer so we can start fresh here
      clearTimeout(this.refreshTimer)

      let filingId = null
      if (this.$route !== undefined) filingId = +this.$route.query.filing_id // if missing, this is NaN

      // only consider refreshing the dashboard if we came from a filing
      if (!filingId) return

      const isInFilingHistory = this.historyFilings.filter(el => el.filingId === filingId).length > 0
      const isInTodoList = this.todoListFilings.filter(el => el.id === filingId).length > 0

      // if this filing is NOT in the to-do list and IS in the filing history list, do nothing - there is no problem
      if (!isInTodoList && isInFilingHistory) return

      // if this filing is in the to-do list, mark it as in-progress for to-do list to format differently
      if (isInTodoList) {
        this.inProcessFiling = filingId
      }

      // check for updated status to reload dashboard
      this.checkFilingStatusCount = 0
      this.checkFilingStatus(filingId)
    },

    checkFilingStatus (filingId) {
      // check whether this filing's status has changed - recursive, runs approx. every 1 second for up to 10 seconds

      this.checkFilingStatusCount++

      // stop this cycle after 10 iterations
      if (this.checkFilingStatusCount > 10) {
        this.inProcessFiling = null
        return
      }

      // get current filing status
      let url = this.entityIncNo + '/filings/' + filingId
      axios.get(url).then(res => {
        // if the filing status is now COMPLETE, reload the dashboard
        if (res && res.data && res.data.filing && res.data.filing.header &&
          res.data.filing.header.status === 'COMPLETED') {
          this.setTriggerDashboardReload(true)
        } else {
          // call this function again in 1 second
          let vue = this
          this.refreshTimer = setTimeout(() => {
            vue.checkFilingStatus(filingId)
          }, 1000)
        }
      }).catch(() => {
        // call this function again in 1 second
        let vue = this
        this.refreshTimer = setTimeout(() => {
          vue.checkFilingStatus(filingId)
        }, 1000)
      })
    }
  },
  mounted () {
    // Flag Usage Example.
    // console.log(this.flags.coopsVersion)
    this.checkToReloadDashboard()
  },
  watch: {
    historyFilings () {
      this.checkToReloadDashboard()
    },
    todoListFilings () {
      this.checkToReloadDashboard()
    }
  },
  destroyed () {
    // kill the refresh timer if it is running
    clearTimeout(this.refreshTimer)
  }
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/theme.scss';

section header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  h2 {
    font-size: 1.125rem;
  }
}

.dashboard-content {
  display: flex
}

.dashboard-content__main {
  flex: 1 1 auto;
  z-index: 1
}

.dashboard-content__aside {
  margin-left: 2rem
}
</style>
