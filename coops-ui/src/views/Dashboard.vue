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
              <todo-list @todo-count="todoCount = $event" @has-blocker-filing="hasBlockerFiling = $event" />
            </section>
            <section>
              <header>
                <h2 class="mb-3">Recent Filing History <span class="text-muted">({{filedCount}})</span></h2>
              </header>
              <filing-history-list @filed-count="filedCount = $event"/>
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
import TodoList from '@/components/Dashboard/TodoList.vue'
import FilingHistoryList from '@/components/Dashboard/FilingHistoryList.vue'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'
import DirectorListSm from '@/components/Dashboard/DirectorListSm.vue'
import { mapState, mapActions } from 'vuex'

export default {
  name: 'Dashboard',

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
      filedCount: 0
    }
  },

  methods: {
    ...mapActions(['setCurrentFilingStatus']),

    goToStandaloneDirectors () {
      this.setCurrentFilingStatus('NEW')
      this.$router.push({ name: 'standalone-directors', params: { id: 0 } }) // 0 means "new COD filing"
    },

    goToStandaloneAddresses () {
      this.setCurrentFilingStatus('NEW')
      this.$router.push({ name: 'standalone-addresses', params: { id: 0 } }) // 0 means "new COA filing"
    }
  }
}
</script>

<style lang="scss" scoped>
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
