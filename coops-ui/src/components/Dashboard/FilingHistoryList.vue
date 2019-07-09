<template>
  <div v-if="filedItems">
    <v-expansion-panel v-if="filedItems">
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

     <!-- No Results Message -->
    <v-card class="no-results" flat v-if="filedItems.length === 0">
      <v-card-text>
        <div class="no-results__title">You have no filing history</div>
        <div class="no-results__subtitle">Your completed filings and transactions will appear here</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import Vue2Filters from 'vue2-filters'
import axios from '@/axios-auth'

export default {
  name: 'FilingHistoryList',

  mixins: [Vue2Filters.mixin],

  data () {
    return {
      filedItems: null
    }
  },

  computed: {
    corpNum () {
      return this.$store.state.corpNum
    },
    currentDate () {
      return this.$store.state.currentDate
    }
  },

  mounted () {
    // reload data for this page
    this.getFiledItems()
  },

  methods: {
    getFiledItems () {
      if (this.corpNum) {
        var url = this.corpNum + '/filings'
        axios.get(url).then(response => {
          if (response && response.data) {
            // this.filedItems = response.data
            // TODO - build actual data from response
            this.filedItems = [
              {
                name: 'Annual Report (2014)',
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
            this.$emit('filing-count', this.filedItems.length)
          } else {
            console.log('getFiledItems() error - invalid response data')
            this.$emit('filing-count', 0)
          }
        }).catch(error => console.error('getFiledItems() error =', error))
      }
    },
    downloadAll (item) {
      // console.log('downloadAll(), item =', item)
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new filed items
      this.getFiledItems()
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"
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
      width 100%
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
   .no-results
    flex-direction column
</style>
