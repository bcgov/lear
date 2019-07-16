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
    <v-card class="no-results" flat v-if="filedItems.length === 0 && !errorMessage">
      <v-card-text>
        <div class="no-results__title">You have no filing history</div>
        <div class="no-results__subtitle">Your completed filings and transactions will appear here</div>
      </v-card-text>
    </v-card>

    <!-- ErrorMessage -->
    <v-card class="network-error" flat v-if="filedItems.length === 0 && errorMessage">
      <v-card-text>
        <div class="network-error__title">{{errorMessage}}</div>
        <div class="no-results__subtitle">Your completed filings and transactions will normally appear here</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import Vue2Filters from 'vue2-filters'
import axios from '@/axios-auth'
import { mapState } from 'vuex'
import { isEmpty } from 'lodash'

export default {
  name: 'FilingHistoryList',

  mixins: [Vue2Filters.mixin],

  data () {
    return {
      filedItems: null,
      errorMessage: null
    }
  },

  computed: {
    ...mapState(['corpNum'])
  },

  mounted () {
    // reload data for this page
    this.getFiledItems()
  },

  methods: {
    getFiledItems () {
      this.filedItems = []
      this.errorMessage = null
      if (this.corpNum) {
        var url = this.corpNum + '/filings'
        axios.get(url).then(response => {
          if (response && response.data && response.data.filings) {
            // sort by id descending (ie, latest to earliest)
            const filings = response.data.filings.sort(
              (a, b) => (b.filing.header.filingId - a.filing.header.filingId)
            )
            // create filed items
            for (let i = 0; i < filings.length; i++) {
              const filing = response.data.filings[i].filing
              switch (filing.header.name) {
                case 'annual_report':
                  this.loadAnnualReport(filing)
                  break
                case 'change_of_directors':
                  this.loadChangeOfDirectors(filing)
                  break
                case 'change_of_address':
                  this.loadChangeOfAddress(filing)
                  break
                default:
                  console.log('ERROR - got unknown filing =', filing)
                  break
              }
            }
          } else {
            console.log('getFiledItems() error - invalid Filings')
            this.errorMessage = 'Oops, could not parse data from server'
          }
          this.$emit('filed-count', this.filedItems.length)
        }).catch(error => {
          console.error('getFiledItems() error =', error)
          this.errorMessage = 'Oops, could not load data from server'
        })
      }
    },

    loadAnnualReport (filing) {
      if (!isEmpty(filing.annualReport)) {
        const agmYear = filing.annualReport.annualGeneralMeetingDate.substring(0, 4)
        // TODO - finish implementation
        const item = {
          name: `Annual Report (${agmYear})`,
          filingAuthor: filing.annualReport.certifiedBy,
          filingDate: filing.header.date,
          filingStatus: filing.header.status,
          filingDocuments: [{ name: 'Annual Report', url: '' }]
        }
        if (!isEmpty(filing.changeOfDirectors)) {
          // TODO
          item.filingDocuments.push({ name: 'Director Change (AGM)', url: '' })
        }
        if (!isEmpty(filing.changeOfAddress)) {
          // TODO
          item.filingDocuments.push({ name: 'Address Change (AGM)', url: '' })
        }
        this.filedItems.push(item)
      }
    },

    loadChangeOfDirectors (filing) {
      if (!isEmpty(filing.changeOfDirectors)) {
        const item = {
          name: 'Director Change',
          filingAuthor: filing.changeOfDirectors.certifiedBy,
          filingDate: filing.header.date,
          filingStatus: filing.header.status,
          filingDocuments: [{ name: 'Director Change', url: '' }]
        }
        this.filedItems.push(item)
      }
    },

    loadChangeOfAddress (filing) {
      if (!isEmpty(filing.changeOfAddress)) {
        const item = {
          name: 'Address Change',
          filingAuthor: filing.changeOfAddress.certifiedBy,
          filingDate: filing.header.date,
          filingStatus: filing.header.status,
          filingDocuments: [{ name: 'Address Change', url: '' }]
        }
        this.filedItems.push(item)
      }
    },

    downloadAll (item) {
      // TODO
      console.log('downloadAll(), item =', item)
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
