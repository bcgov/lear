<template>
  <div>

    <div class="loading-container fade-out">
      <div class="loading__content">
        <v-progress-circular color="primary" :size="50" indeterminate></v-progress-circular>
      </div>
    </div>

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
          <h2>To Do</h2>
          <v-card flat>
            <ul class="dashboard-list">
              <li class="dashboard-list-item"
                v-for="(item, index) in orderBy(todoItems, 'name', -1)"
                v-bind:key="index">
                <div class="name">{{item.name}}</div>
                <div class="actions">
                  <v-btn color="primary" depressed @click="fileAnnualReport" :disabled="!item.enabled">File Now</v-btn>
                </div>
              </li>
            </ul>
          </v-card>
        </section>
        <section>
          <h2>Filing History</h2>
            <v-alert v-model="filingAlert" type="success" class="mb-4" transition="slide-y-transition">
              2018 Annual Report was filed successfully. You can download your transaction below.
            </v-alert>
            <v-card flat>
              <ul>
                <li class="dashboard-list-item"
                  v-for="(item, index) in orderBy(filedItems, 'name', -1)"
                  v-bind:key="index">
                  <div class="name">{{item.name}}</div>
                  <div class="price">{{item.price}}</div>
                  <div class="actions">
                    <v-btn depressed :disabled="item.enabled">Download</v-btn>
                  </div>
                </li>
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
    name: "DashboardSuccess",
    mixins: [Vue2Filters.mixin],
    components: {
      EntityInfo,
    },

    data () {
      return {
        todoItems: [
          { name: 'Annual Report (2019)', enabled: true }
        ],

        filedItems: [
          { name: 'Annual Report (2018)', price: '$70.00', enabled: false }
        ],

        showLoading: false,
        filingAlert: true,
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

  .dashboard-list-item
    display flex
    align-items center
    padding 1rem
    background #fff
    font-size 0.875rem

    .name
      margin-right auto
      font-weight 700

    .price
      margin-right 3rem
      font-weight 700

    .v-btn
      min-width 8rem
      font-weight 500

  .dashboard-list-item + .dashboard-list-item
    border-top 1px solid $gray3

  .v-alert
    border-width 0
</style>