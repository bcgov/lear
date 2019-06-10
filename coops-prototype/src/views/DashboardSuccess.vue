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
          <v-card>
            <ul class="todo-list">
              <li class="dashboard-list-item"><span class="text-muted">You have no Annual Reports to File</span></li>
            </ul>
          </v-card>
        </section>
        <section>
          <h2>Filing History <span class="text-muted">(1)</span></h2>
            <v-card>
              <!--
              <v-alert v-model="filingAlert" type="success" transition="slide-y-transition">
                2018 Annual Report was filed successfully. You can download your transaction below.
              </v-alert>
              -->
              <ul class="filing-history">
                <li class="dashboard-list-item"
                  v-for="(item, index) in orderBy(filedItems, 'name', -1)"
                  v-bind:key="index">
                  <div class="name">{{item.name}}</div>
                  <div class="date"><span class="text-muted">{{ moment(item).format('MM/DD/YYYY') }}</span></div>
                  <div class="status"><span class="text-muted">{{ item.status }}</span></div>
                  <div class="price">{{item.price}}</div>
                  <div class="actions">
                    <a class="v-btn download-btn" v-bind:href="'/downloads/receipt.pdf'" target="_blank">Download</a>
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
  import moment from 'moment'

  Vue.use(Vue2Filters)

  export default {
    name: "DashboardSuccess",
    mixins: [Vue2Filters.mixin],
    components: {
      EntityInfo,
    },

    data () {
      return {
        publicPath: process.env.BASE_URL,

        todoItems: [
          { }
        ],

        filedItems: [
          { name: 'Annual Report (2019)', status: 'Completed', price: '$70.00', enabled: false }
        ],

        showLoading: false,
        filingAlert: true,
        someDate: '',
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
      },

      moment: function (date) {
        return moment(date);
      },

      date: function (date) {
        return moment(date).format('MMMM Do YYYY');
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

    .price
      flex 1 1 auto
      font-weight 700
      text-align center

    .date
      flex 1 1 auto
      margin-left 5rem
      text-align center

    .status
      flex 1 1 auto
      text-align center

    .v-btn
      min-width 10rem
      font-weight 500

  .todo-list .name
    margin-right auto

  .dashboard-list-item + .dashboard-list-item
    border-top 1px solid $gray3

  .v-alert
    border-width 0

  .text-muted
    color $gray6
    font-weight 400

  .download-btn
    color #000
</style>
