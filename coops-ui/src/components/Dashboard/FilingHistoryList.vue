<template>
  <div>
    <DownloadErrorDialog
      :dialog="downloadErrorDialog"
      @close="downloadErrorDialog = false"
    />

    <v-expansion-panels v-if="filedItems && filedItems.length > 0" v-model="panel" accordion>
      <v-expansion-panel
        class="align-items-top filing-history-item"
        v-for="(item, index) in filedItems"
        v-bind:key="index">
        <v-expansion-panel-header>
          <div class="list-item">
            <div class="filing-type">
              <div class="list-item__title mb-1">{{item.name}}</div>
              <div class="list-item__subtitle">
                FILED AND PAID (filed by {{item.filingAuthor}} on {{item.filingDate}})
              </div>
            </div>
            <div class="filing-view-docs mr-3">
              <span v-if="panel === index && !item.paperOnly">Hide Documents</span>
              <span v-else-if="panel === index && item.paperOnly">Close</span>
              <span v-else-if="item.paperOnly">Request a Copy</span>
              <span v-else>View Documents</span>
            </div>
          </div>
        </v-expansion-panel-header>
        <v-expansion-panel-content>
          <ul v-if="!item.paperOnly" class="list document-list">
            <li class="list-item"
              v-for="(document, index) in item.filingDocuments"
              v-bind:key="index">
              <v-btn class="list-item__btn" text color="primary" @click="downloadDocument(document)"
                :disabled="loadingDocument" :loading="loadingDocument">
                <img class="list-item__icon" src="@/assets/images/icons/file-pdf-outline.svg" />
                <div class="list-item__title">{{document.name}}</div>
              </v-btn>
            </li>
            <li class="list-item"  v-if="item.paymentToken">
              <v-btn class="list-item__btn" text color="primary" @click="downloadReceipt(item)"
                :disabled="loadingReceipt" :loading="loadingReceipt">
                <img class="list-item__icon" src="@/assets/images/icons/file-pdf-outline.svg" />
                <div class="list-item__title">Receipt</div>
              </v-btn>
            </li>
          </ul>
          <div v-if="!item.paperOnly" class="documents-actions-bar">
            <v-btn class="download-all-btn" color="primary" @click="downloadAll(item)"
              :disabled="loadingAll" :loading="loadingAll">
              Download All
            </v-btn>
          </div>
          <v-card v-if="item.paperOnly" class="paper-filings" flat>
            <v-card-text>
              <div class="paper-filings__text">
                Filings completed <b>before March 10, 2019</b> are only available from the BC Registry as paper
                documents.
                <br><br>
                To request copies of paper documents, contact BC Registry Staff with the document you require and
                the name and incorporation number of your associtation:
                <br><br>
                <p class="paper-filings__text">
                  <v-icon medium>mdi-phone</v-icon>
                  <a href="tel:+1-877-526-1526">1 877 526-1526</a>
                </p>
                <p class="paper-filings__text">
                  <v-icon medium>mdi-email</v-icon>
                  <a href="mailto:BCRegistries@gov.bc.ca"
                    >BCRegistries@gov.bc.ca</a>
                </p>
              </div>
            </v-card-text>
          </v-card>
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- No Results Message -->
    <v-card class="no-results" flat v-if="filedItems && filedItems.length === 0">
      <v-card-text>
        <div class="no-results__title">You have no filing history</div>
        <div class="no-results__subtitle">Your completed filings and transactions will appear here</div>
      </v-card-text>
    </v-card>

  </div>
</template>

<script lang="ts">
import ExternalMixin from '@/mixins/external-mixin'
import axios from '@/axios-auth'
import { mapState } from 'vuex'
import DownloadErrorDialog from '@/components/Dashboard/DownloadErrorDialog.vue'

export default {
  name: 'FilingHistoryList',

  mixins: [ExternalMixin],

  components: {
    DownloadErrorDialog
  },

  data () {
    return {
      downloadErrorDialog: false,
      panel: null, // currently expanded panel
      filedItems: null,
      loadingDocument: false,
      loadingReceipt: false,
      loadingAll: false
    }
  },

  computed: {
    ...mapState(['entityIncNo', 'filings', 'entityName'])
  },

  created () {
    // load data into this page
    this.loadData()
  },

  methods: {
    loadData () {
      this.filedItems = []

      // create filed items
      for (let i = 0; i < this.filings.length; i++) {
        const filing = this.filings[i].filing
        if (filing && filing.header) {
          if (filing.header.date < '2019-03-08' || filing.header.availableOnPaperOnly) {
            this.loadPaperFiling(filing)
          } else {
            switch (filing.header.name) {
              case 'annualReport':
                this.loadAnnualReport(filing)
                break
              case 'changeOfDirectors':
                this.loadReport('Director Change', filing, filing.changeOfDirectors)
                break
              case 'changeOfAddress':
                this.loadReport('Address Change', filing, filing.changeOfAddress)
                break
              case 'changeOfName':
                this.loadReport('Legal Name Change', filing, filing.changeOfName)
                break
              case 'specialResolution':
                this.loadReport('Special Resolution', filing, filing.specialResolution)
                break
              case 'voluntaryDissolution':
                this.loadReport('Voluntary Dissolution', filing, filing.voluntaryDissolution)
                break
              default:
                this.loadPaperFiling(filing)
                break
            }
          }
        } else {
          console.log('ERROR - invalid filing or filing header =', filing)
        }
      }

      this.$emit('filed-count', this.filedItems.length)
      this.$emit('filings-list', this.filedItems)

      // if needed, highlight a specific filing
      // NB: use unary plus operator to cast string to number
      const highlightId = +this.$route.query.filing_id // may be NaN (which is false)
      if (highlightId) { this.highlightFiling(highlightId) }
    },

    loadAnnualReport (filing) {
      if (filing.annualReport) {
        const date = filing.annualReport.annualGeneralMeetingDate
        if (date) {
          const agmYear = +date.substring(0, 4)
          const item = {
            name: `Annual Report (${agmYear})`,
            filingId: filing.header.filingId,
            filingAuthor: filing.header.certifiedBy,
            filingDate: filing.header.date,
            paymentToken: filing.header.paymentToken,
            filingDocuments: [{
              filingId: filing.header.filingId,
              name: 'Annual Report',
              documentName: `${this.entityIncNo} - Annual Report (${agmYear}) - ${filing.header.date}.pdf`
            }],
            paperOnly: false
          }
          this.filedItems.push(item)
        } else {
          console.log('ERROR - invalid date in filing =', filing)
        }
      } else {
        console.log('ERROR - invalid annualReport in filing =', filing)
      }
    },

    loadReport (title, filing, section) {
      if (section) {
        const item = {
          name: title,
          filingId: filing.header.filingId,
          filingAuthor: filing.header.certifiedBy,
          filingDate: filing.header.date,
          paymentToken: filing.header.paymentToken,
          filingDocuments: [{
            filingId: filing.header.filingId,
            name: title,
            documentName: `${this.entityIncNo} - ${title} - ${filing.header.date}.pdf`
          }],
          paperOnly: false
        }
        this.filedItems.push(item)
      } else {
        console.log(`ERROR - invalid ${title} in filing =`, filing)
      }
    },

    loadPaperFiling (filing) {
      // split name on camelcase and capitalize first letters
      let name = filing.header.name.split(/(?=[A-Z])/).join(' ')
      name = name.charAt(0).toLocaleUpperCase() + name.slice(1)
      const item = {
        name: name,
        filingAuthor: 'Registry Staff',
        filingDate: filing.header.date,
        filingYear: filing.header.date.slice(0, 4),
        paymentToken: null,
        filingDocuments: [{
          filingId: filing.header.filingId,
          name: name,
          documentName: null
        }],
        paperOnly: true
      }
      this.filedItems.push(item)
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

    async downloadDocument (filingDocument) {
      this.loadingDocument = true
      await this.downloadOneDocument(filingDocument)
      this.loadingDocument = false
    },

    async downloadOneDocument (filingDocument) {
      const url = this.entityIncNo + '/filings/' + filingDocument.filingId
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
        corpName: this.entityName,
        filingDateTime: filing.filingDate, // TODO: format as needed
        fileName: 'receipt' // not used
      }
      const config = {
        headers: { 'Accept': 'application/pdf' },
        responseType: 'blob' as 'json',
        baseURL: sessionStorage.getItem('PAY_API_URL') + 'payment-requests/'
      }

      await axios.post(url, data, config).then(response => {
        if (response) {
          const fileName = `${this.entityIncNo} - Receipt - ${filing.filingDate}.pdf`

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
      if (filing.paymentToken) {
        await this.downloadOneReceipt(filing)
      }
      this.loadingAll = false
    }
  },

  watch: {
    filings () {
      // if filings changes, reload them
      // (does not fire on initial page load)
      this.loadData()
    }
  }
}
</script>

<style lang="scss" scoped>
@import "@/assets/styles/theme.scss";

.list-item {
  align-items: flex-start;
  justify-content: space-between;
  padding: 0;
}

.filing-type {
  flex-basis: 33.3333%;
  flex: 1 1 auto;
}

.filing-status {
  width: 25%;
  color: $gray6;
}

.filing-view-docs {
  flex: 0 0 auto;
  width: 30%;
  text-align: right;
  font-weight: 700;
}

  // Document List
.document-list {
  border-top: 1px solid $gray3;
  padding-left: 0;

  .list-item {
    padding: 0.25rem 0;
  }

  .v-btn {
    padding: 0 0.5rem 0 0.25rem;
  }
}

  // Documents Actions Bar
.documents-actions-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid $gray3;

  .download-all-btn {
    min-width: 8rem;
  }
}

// Past Filings
.past-filings {
  border-top: 1px solid $gray3;
  text-align: center;

  .past-filings__text {
    margin-top: 0.25rem;
    color: $gray6;
    font-size: 0.875rem;
    font-weight: 500;
  }
}
.paper-filings {
  border-top: 1px solid $gray3;
  text-align: left;

  .paper-filings__text {
    margin-top: 0.2rem;
    color: $gray9;
    font-size: 0.8rem;
    font-weight: 400;
    line-height: 1rem;

    a {
      color: $gray7;
      margin-left: 1rem;
    }
  }
}
</style>
