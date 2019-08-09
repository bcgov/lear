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
          <h1>Dashboard</h1>
        </header>

        <div class="dashboard-content">
          <div class="dashboard-content__main">
            <section>
              <header>
                <h2>To Do <span class="text-muted">({{todoCount}})</span></h2>
              </header>
              <todo-list @todo-count="todoCount = $event" @has-blocker-filing="hasBlockerFiling = $event" />
            </section>

            <section>
              <header>
                <h2>Recent Filing History <span class="text-muted">({{filedCount}})</span></h2>
              </header>
              <filing-history-list @filed-count="filedCount = $event"/>
            </section>
          </div>

          <aside class="dashboard-content__aside">
            <section>
              <header>
                <h2>Office Addresses</h2>
                <v-btn id="btn-standalone-addresses" flat small color="primary" :disabled="hasBlockerFiling"
                       @click.native.stop="goToStandaloneAddresses()">
                  <v-icon small>edit</v-icon>
                  <span>EDIT</span>
                </v-btn>
              </header>
              <v-card flat>
                <address-list-sm></address-list-sm>
              </v-card>
            </section>

            <section>
              <header>
                <h2>Current Directors</h2>
                <v-btn id="btn-standalone-directors" flat small color="primary" :disabled="hasBlockerFiling"
                       @click.native.stop="goToStandaloneDirectors()">
                  <v-icon small>edit</v-icon>
                  <span>EDIT</span>
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

<script lang="ts">
import { Vue } from 'vue-property-decorator'
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

  created () {
    // TODO: load data for all subcomponents here
    // see axios.all()
    // in case of error, display popup
  },
  methods: {
    ...mapActions(['setCurrentFilingStatus']),

    goToStandaloneDirectors () {
      this.setCurrentFilingStatus('NEW')
      this.$router.push('/standalone-directors')
    },
    goToStandaloneAddresses () {
      this.$router.push('/standalone-addresses')
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .text-muted
    color $gray5

  h1
    margin-bottom 0

  .dashboard-content
    display flex

  .dashboard-content__main
    flex 1 1 auto

  .dashboard-content__aside
    margin-left 2rem

  section header
    display flex
    flex-direction row

    .v-btn
      margin-top 0
      margin-right 0
      margin-left auto
</style>
