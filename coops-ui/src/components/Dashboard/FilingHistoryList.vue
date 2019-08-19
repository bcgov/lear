<template>
  <div>
    <v-dialog v-model="downloadErrorDialog" width="30rem">
      <v-card>
        <v-card-title>Unable to Download Document</v-card-title>
        <v-card-text>
          <p class="genErr">We were unable to download your filing history document(s).</p>
          <p class="genErr">If this error persists, please contact us.</p>
          <p class="genErr">
            <v-icon small>phone</v-icon>
            <a href="tel:+1-250-952-0568" class="error-dialog-padding">250 952-0568</a>
          </p>
          <p class="genErr">
            <v-icon small>email</v-icon>
            <a href="mailto:SBC_ITOperationsSupport@gov.bc.ca" class="error-dialog-padding"
              >SBC_ITOperationsSupport@gov.bc.ca</a>
          </p>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions>
          <v-btn color="primary" flat @click="downloadErrorDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-expansion-panel v-if="filedItems && filedItems.length > 0" v-model="panel">
      <v-expansion-panel-content
        class="filing-history-list"
        v-for="(item, index) in filedItems"
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
            <v-btn class="list-item__btn" flat color="primary" @click="downloadDocument(document)"
              :disabled="loadingDocument" :loading="loadingDocument">
              <img class="list-item__icon" src="@/assets/images/icons/file-pdf-outline.svg" />
              <div class="list-item__title">{{document.name}}</div>
            </v-btn>
          </li>
          <li class="list-item">
            <v-btn class="list-item__btn" flat color="primary" @click="downloadReceipt(item)"
              :disabled="loadingReceipt" :loading="loadingReceipt">
              <img class="list-item__icon" src="@/assets/images/icons/file-pdf-outline.svg" />
              <div class="list-item__title">Receipt</div>
            </v-btn>
          </li>
        </ul>
        <div class="documents-actions-bar">
          <v-btn class="download-all-btn" color="primary" @click="downloadAll(item)"
            :disabled="loadingAll" :loading="loadingAll">
            Download All
          </v-btn>
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
      downloadErrorDialog: false,
      panel: null, // currently expanded panel
      filedItems: null,
      errorMessage: null,
      loadingDocument: false,
      loadingReceipt: false,
      loadingAll: false
    }
  },

  computed: {
    ...mapState(['corpNum'])
  },

  mounted () {
    // load data for this page
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
            // sort by date descending (ie, latest to earliest)
            const filings = response.data.filings.sort(
              (a, b) => (b.filing.header.date - a.filing.header.date)
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
                    console.log('ERROR - got unknown filing name =', filing)
                    break
                }
              } else {
                console.log('ERROR - invalid filing or filing header =', filing)
              }
            }
          } else {
            console.log('getFilings() error - invalid Filings')
            this.errorMessage = 'Oops, could not parse data from server'
          }
          this.$emit('filed-count', this.filedItems.length)
          // if needed, highlight a specific filing
          // NB: use unary plus operator to cast string to number
          const highlightId = +this.$route.query.filing_id // may be NaN (which is false)
          if (highlightId) { this.highlightFiling(highlightId) }
        }).catch(error => {
          console.error('getFilings() error =', error)
          this.errorMessage = 'Oops, could not load data from server'
        })
      }
    },

    highlightFiling (highlightId) {
      // expand the panel of the matching filing
      for (let i = 0; i < this.filedItems.length; i++) {
        // assume there is always a filing document
        if (this.filedItems[i].filingDocuments[0].filingId === highlightId) {
          this.panel = i
          break
        }
      }
    },

    loadAnnualReport (filing) {
      if (filing.annualReport) {
        const date = filing.annualReport.annualGeneralMeetingDate
        if (date) {
          const agmYear = +date.substring(0, 4)
          const item = {
            name: `Annual Report (${agmYear})`,
            filingAuthor: filing.annualReport.certifiedBy,
            filingDate: filing.header.date,
            paymentToken: filing.header.paymentToken,
            filingStatus: filing.header.status,
            filingDocuments: [{
              filingId: filing.header.filingId,
              name: 'Annual Report',
              documentName: `${this.corpNum} - Annual Report (${agmYear}) - ${filing.header.date}.pdf`
            }]
          }
          // check if there was also a Change Of Directors
          if (filing.changeOfDirectors) {
            item.filingDocuments.push({
              filingId: filing.header.filingId,
              name: 'Director Change (AGM)',
              documentName: `${this.corpNum} - Director Change (AGM ${agmYear}) - ${filing.header.date}.pdf`
            })
          }
          // check if there was also a Change Of Address
          if (filing.changeOfAddress) {
            item.filingDocuments.push({
              filingId: filing.header.filingId,
              name: 'Address Change (AGM)',
              documentName: `${this.corpNum} - Address Change (AGM ${agmYear}) - ${filing.header.date}.pdf`
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
          paymentToken: filing.header.paymentToken,
          filingStatus: filing.header.status,
          filingDocuments: [{
            filingId: filing.header.filingId,
            name: 'Director Change',
            documentName: `${this.corpNum} - Director Change - ${filing.header.date}.pdf`
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
          paymentToken: filing.header.paymentToken,
          filingStatus: filing.header.status,
          filingDocuments: [{
            filingId: filing.header.filingId,
            name: 'Address Change',
            documentName: `${this.corpNum} - Address Change - ${filing.header.date}.pdf`
          }]
        }
        this.filedItems.push(item)
      } else {
        console.log('ERROR - invalid changeOfAddress in filing =', filing)
      }
    },

    async downloadDocument (filingDocument) {
      this.loadingDocument = true
      await this.downloadOneDocument(filingDocument)
      this.loadingDocument = false
    },

    async downloadOneDocument (filingDocument) {
      const url = this.corpNum + '/filings/' + filingDocument.filingId
      const headers = { 'Accept': 'application/pdf' }

      await axios.get(url, { headers: headers, responseType: 'blob' as 'json' }).then(response => {
        if (response) {
          /* solution from https://github.com/axios/axios/issues/1392 */

          // it is necessary to create a new blob object with mime-type explicitly set
          // otherwise only Chrome works like it should
          const blob = new Blob([response.data], { type: 'application/pdf' })

          // IE doesn't allow using a blob object directly as link href
          // instead it is necessary to use msSaveOrOpenBlob
          if (window.navigator && window.navigator.msSaveOrOpenBlob) {
            window.navigator.msSaveOrOpenBlob(blob, filingDocument.documentName)
          } else {
            // for other browsers, create a link pointing to the ObjectURL containing the blob
            const url = window.URL.createObjectURL(blob)
            const a = window.document.createElement('a')
            window.document.body.appendChild(a)
            a.setAttribute('style', 'display: none')
            a.href = url
            a.download = filingDocument.documentName
            a.click()
            window.URL.revokeObjectURL(url)
            a.remove()
          }
        } else {
          console.log('downloadOneDocument() error - null response')
          this.downloadErrorDialog = true
        }
      }).catch(error => {
        console.error('loadOneDocument() error =', error)
        this.downloadErrorDialog = true
      })
    },

    async downloadReceipt (filing) {
      this.loadingReceipt = true
      await this.downloadOneReceipt(filing)
      this.loadingReceipt = false
    },

    async downloadOneReceipt (filing) {
      const url = filing.paymentToken + '/receipts'
      const data = {
        corpName: this.corpNum,
        filingDateTime: filing.filingDate, // TODO: format as needed
        fileName: 'receipt' // not used
      }
      const config = {
        headers: { 'Accept': 'application/pdf' },
        responseType: 'blob' as 'json',
        baseURL: this.payAPIURL + 'payments/'
      }

      await axios.post(url, data, config).then(response => {
        if (response) {
          const fileName = `${this.corpNum} - Receipt - ${filing.filingDate}.pdf`

          /* solution from https://github.com/axios/axios/issues/1392 */

          // it is necessary to create a new blob object with mime-type explicitly set
          // otherwise only Chrome works like it should
          const blob = new Blob([response.data], { type: 'application/pdf' })

          // IE doesn't allow using a blob object directly as link href
          // instead it is necessary to use msSaveOrOpenBlob
          if (window.navigator && window.navigator.msSaveOrOpenBlob) {
            window.navigator.msSaveOrOpenBlob(blob, fileName)
          } else {
            // for other browsers, create a link pointing to the ObjectURL containing the blob
            const url = window.URL.createObjectURL(blob)
            const a = window.document.createElement('a')
            window.document.body.appendChild(a)
            a.setAttribute('style', 'display: none')
            a.href = url
            a.download = fileName
            a.click()
            window.URL.revokeObjectURL(url)
            a.remove()
          }
        } else {
          console.log('downloadOneReceipt() error - null response')
          this.downloadErrorDialog = true
        }
      }).catch(error => {
        console.error('downloadOneReceipt() error =', error)
        this.downloadErrorDialog = true
      })
    },

    async downloadAll (filing) {
      this.loadingAll = true
      // first download document(s)
      for (let i = 0; i < filing.filingDocuments.length; i++) {
        await this.downloadOneDocument(filing.filingDocuments[i])
      }
      // finally download receipt
      await this.downloadOneReceipt(filing)
      this.loadingAll = false
    }
  },

  watch: {
    corpNum (val) {
      // if Corp Num changes, get new filings
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

    .list-item__btn
      margin 0.25rem 0
      padding 0 0.5rem 0 0.25rem

   // Documents Actions Bar
  .documents-actions-bar
    padding-top 1rem
    display flex
    border-top 1px solid $gray3

    .download-all-btn
      margin-left auto
      margin-right 0
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
