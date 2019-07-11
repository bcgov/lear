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
              <todo-list @todo-count="todoCount = $event"/>
            </section>

            <section>
              <header>
                <h2>Recent Filing History <span class="text-muted">({{filingCount}})</span></h2>
              </header>
              <filing-history-list @filing-count="filingCount = $event"/>
            </section>
          </div>

          <aside class="dashboard-content__aside">
            <section>
              <header>
                <h2>Registered Office Addresses</h2>
              </header>
              <v-card flat>
                <address-list-sm></address-list-sm>
              </v-card>
            </section>
            <section>
              <header>
                <h2>Current Directors</h2>
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
      filingCount: 0
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

  h1
    margin-bottom 0

  h2
    margin-bottom 0.25rem
    margin-top 3rem
    font-size 1.125rem
    font-weight 500

  .dashboard-content
    display flex

  .dashboard-content__main
    flex 1 1 auto

  .dashboard-content__aside
    margin-left 2rem

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
</style>
