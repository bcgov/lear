<template>
  <div>
    <v-expansion-panel v-if="filedItems && filedItems.length > 0" v-model="panel">
      <v-expansion-panel-content
        class="filing-history-list"
        v-for="(item, index) in orderBy(filedItems, 'filingDate', -1)"
        v-bind:key="index">
        <template v-slot:header>
          <div class="list-item">
            <div class="list-item__title">{{item.name}}</div>
            <div class="list-item__subtitle">Filed by {{item.filingAuthor}} on {{item.filingDate}}</div>
          </div>
          <div class="v-expansion-panel__header__status">FILED AND PAID</div>
          <div class="v-expansion-panel__header__icon">
            <span v-if="panel === index">Hide Documents</span>
            <span v-else>View Documents</span>
          </div>
        </template>
        <ul class="list document-list">
          <li class="list-item"
            v-for="(document, index) in item.filingDocuments"
            v-bind:key="index">
            <a href="#" @click="loadDocument(document)">
              <img class="list-item__icon" src="@/assets/images/icons/file-pdf-outline.svg" />
              <div class="list-item__title">{{document.name}}</div>
            </a>
          </li>
          <li class="list-item">
            <a href="#">
              <img class="list-item__icon" src="@/assets/images/icons/file-pdf-outline.svg" />
              <div class="list-item__title">Receipt</div>
            </a>
          </li>
        </ul>
        <div class="documents-actions-bar">
          <v-btn class="download-all-btn" color="primary" @click="downloadAll(item)">Download All</v-btn>
        </div>
      </v-expansion-panel-content>
    </v-expansion-panel>

    <!-- No Results Message -->
    <v-card class="no-results" flat v-if="filedItems && filedItems.length === 0 && !errorMessage">
      <v-card-text>
        <div class="no-results__title">You have no filing history</div>
        <div class="no-results__subtitle">Your completed filings and transactions will appear here</div>
      </v-card-text>
    </v-card>

    <!-- Error Message -->
    <v-card class="network-error" flat v-if="filedItems && filedItems.length === 0 && errorMessage">
      <v-card-text>
        <div class="network-error__title">{{errorMessage}}</div>
        <div class="no-results__subtitle">Your completed filings and transactions will normally appear here</div>
      </v-card-text>
    </v-card>

    <!-- Past Filings Message -->
    <v-card class="past-filings" flat>
      <v-card-text>
        <div class="past-filings__text">
          Filings completed before August 21, 2019 will be available from the BC Registry as printed
          documents.<br>Please contact us at <a href="tel:+1-250-952-0568">250 952-0568</a> to request
          paper copies of these past filings.
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import Vue2Filters from 'vue2-filters'
import axios from '@/axios-auth'
import { mapState, mapActions } from 'vuex'

export default {
  name: 'FilingHistoryList',

  mixins: [Vue2Filters.mixin],

  data () {
    return {
      panel: null, // currently expanded panel
      filedItems: null,
      errorMessage: null
    }
  },

  computed: {
    ...mapState(['corpNum'])
  },

  mounted () {
    // reload data for this page
    this.getFilings()
  },

  methods: {
    ...mapActions(['setFilingHistory']),

    getFilings () {
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

            // store the list of filing history to be used elsewhere
            this.setFilingHistory(filings)

            // create filed items
            for (let i = 0; i < filings.length; i++) {
              const filing = filings[i].filing
              if (filing && filing.header) {
                switch (filing.header.name) {
                  case 'annualReport':
                    this.loadAnnualReport(filing)
                    break
                  case 'changeOfDirectors':
                    this.loadChangeOfDirectors(filing)
                    break
                  case 'changeOfAddress':
                    this.loadChangeOfAddress(filing)
                    break
                  default:
                    console.log('ERROR - got unknown filing =', filing)
                    break
                }
              }
            }
          } else {
            console.log('getFilings() error - invalid Filings')
            this.errorMessage = 'Oops, could not parse data from server'
          }
          this.$emit('filed-count', this.filedItems.length)
        }).catch(error => {
          console.error('getFilings() error =', error)
          this.errorMessage = 'Oops, could not load data from server'
        })
      }
    },

    loadAnnualReport (filing) {
      if (filing.annualReport) {
        const date = filing.annualReport.annualGeneralMeetingDate
        if (date) {
          const agmYear = +date.substring(0, 4)
          // TODO - finish implementation
          const item = {
            name: `Annual Report (${agmYear})`,
            filingAuthor: filing.annualReport.certifiedBy,
            filingDate: filing.header.date,
            filingStatus: filing.header.status,
            filingDocuments: [{
              filingId: filing.header.filingId,
              name: 'Annual Report',
              documentName: `Annual Report (${agmYear}) - ` + filing.header.date
            }]
          }
          if (filing.changeOfDirectors) {
            item.filingDocuments.push({
              filingId: filing.header.filingId,
              name: 'Director Change (AGM)',
              documentName: `Director Change (AGM ${agmYear}) - ` + filing.header.date
            })
          }
          if (filing.changeOfAddress) {
            item.filingDocuments.push({
              filingId: filing.header.filingId,
              name: 'Address Change (AGM)',
              documentName: `Address Change (AGM ${agmYear}) - ` + filing.header.date
            })
          }
          this.filedItems.push(item)
        } else {
          console.log('ERROR - invalid date in filing =', filing)
        }
      } else {
        console.log('ERROR - invalid annualReport in filing =', filing)
      }
    },

    loadChangeOfDirectors (filing) {
      if (filing.changeOfDirectors) {
        const item = {
          name: 'Director Change',
          filingAuthor: filing.changeOfDirectors.certifiedBy,
          filingDate: filing.header.date,
          filingStatus: filing.header.status,
          filingDocuments: [{
            filingId: filing.header.filingId,
            name: 'Director Change',
            documentName: 'Director Change - ' + filing.header.date
          }]
        }
        this.filedItems.push(item)
      } else {
        console.log('ERROR - invalid changeOfDirectors in filing =', filing)
      }
    },

    loadChangeOfAddress (filing) {
      if (filing.changeOfAddress) {
        const item = {
          name: 'Address Change',
          filingAuthor: filing.changeOfAddress.certifiedBy,
          filingDate: filing.header.date,
          filingStatus: filing.header.status,
          filingDocuments: [{
            filingId: filing.header.filingId,
            name: 'Address Change',
            documentName: 'AddressChange - ' + filing.header.date
          }]
        }
        this.filedItems.push(item)
      } else {
        console.log('ERROR - invalid changeOfAddress in filing =', filing)
      }
    },

    loadDocument (filingDocument) {
      var url = this.corpNum + '/filings/' + filingDocument.filingId
      let headers = { 'Accept': 'application/pdf' }

      axios.get(url, { headers: headers, responseType: 'arraybuffer' }).then(response => {
        if (response) {
          /* solution from https://github.com/axios/axios/issues/1392 */

          // It is necessary to create a new blob object with mime-type explicitly set
          // otherwise only Chrome works like it should
          var newBlob = new Blob([response.data], { type: 'application/pdf' })

          // IE doesn't allow using a blob object directly as link href
          // instead it is necessary to use msSaveOrOpenBlob
          if (window.navigator && window.navigator.msSaveOrOpenBlob) {
            window.navigator.msSaveOrOpenBlob(newBlob)
            return
          }

          // For other browsers:
          // Create a link pointing to the ObjectURL containing the blob.
          const data = window.URL.createObjectURL(newBlob)
          var link = document.createElement('a')
          link.href = data
          link.download = filingDocument.documentName
          link.click()
        } else {
          this.errorMessage = 'Oops, could not load data from server'
        }
      }).catch(error => {
        console.error('loadDocument() error =', error)
        this.errorMessage = 'Oops, could not load data from server'
      })
    },

    downloadAll (item) {
      for (let i = 0; i < item.filingDocuments.length; i++) {
        this.loadDocument(item.filingDocuments[i])
      }
    }
  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new filed items
      this.getFilings()
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"

  // Filing History List
  .filing-history-list
    .list-item
      flex-direction column
      align-items flex-start
      padding 0

    .v-expansion-panel__header__status
      font-size 0.875rem
      color $gray6

    .v-expansion-panel__header__icon
      font-size 0.875rem
      font-weight 700

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

   // Documents Actions Bar
  .documents-actions-bar
    padding-top 1rem
    display flex
    border-top 1px solid $gray3

    .v-btn
      margin-right 0

  .download-all-btn
    margin-left auto
    min-width 8rem

  // Past Filings
  .past-filings
    border-top 1px solid $gray3
    text-align center

  .past-filings__text
    margin-top 0.25rem
    color $gray6
    font-size 0.875rem
    font-weight 500
</style>
