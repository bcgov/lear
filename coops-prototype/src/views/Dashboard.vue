<template>
  <div>
    <v-fade-transition>
      <div class="loading-container" v-show="showLoading">
        <div class="loading__content">
          <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
          <div class="loading-msg">{{this.loadingMsg}}</div>
        </div>
      </div>
    </v-fade-transition>
    <EntityInfo/>
    <v-container class="view-container">
      <article>
        <header>
          <h1>Annual Reports</h1>
        </header>
        <section>
          <h2>To Do <span class="text-muted">({{todoItems.length}})</span></h2>
          <v-card>
            <ul class="dashboard-list">
              <li class="dashboard-list-item"
                v-for="(item, index) in orderBy(todoItems, 'name', 1)"
                v-bind:key="index">
                <div class="name">{{item.name}}</div>
                <div class="actions">
                  <v-btn color="primary" @click="fileAnnualReport" :disabled="!item.enabled">File Now</v-btn>
                </div>
              </li>
            </ul>
          </v-card>
        </section>
        <section>
          <h2>Filing History</h2>
          <v-card>
            <ul>
              <li class="dashboard-list-item"><span class="text-muted">You have no previous filings</span></li>
            </ul>
          </v-card>
        </section>
      </article>
    </v-container>
  </div>
</template>

<script lang='ts'>
  import { Component, Vue } from 'vue-property-decorator'
  import EntityInfo from '@/components/EntityInfo.vue'
  import Vue2Filters from 'vue2-filters'

  Vue.use(Vue2Filters)

  export default {
    name: "Dashboard",
    mixins: [Vue2Filters.mixin],
    components: {
      EntityInfo,
    },

    data () {
      return {
        todoItems: [
          // { name: 'Annual Report (2018)', enabled: true },
          { name: 'File 2019 Annual Report', enabled: true }
        ],

        filedItems: [
        ],

        showLoading: false,
        loadingMsg: 'Preparing your Annual Report'
      }
    },

    methods: {
      gotoAnnualReport: function () {
        this.$router.push({ path: '/AnnualReport' })
      },

      fileAnnualReport: function () {
        this.showLoading = true
        setTimeout(() => { this.gotoAnnualReport() })
      }
    }
  }
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  ul
    margin 0
    padding 0

  .dashboard-list-item
    display flex
    align-items center
    padding 1rem
    background #fff
    font-size 0.875rem

    .name
      font-weight 700

    .actions
      margin-left auto

    .v-btn
      min-width 10rem
      font-weight 500

  .dashboard-list-item + .dashboard-list-item
    border-top 1px solid $gray3

  .text-muted
    color $gray6
    font-weight 400
</style>
