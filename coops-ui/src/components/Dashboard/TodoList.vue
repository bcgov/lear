<template>
  <div>
    <ConfirmDialog ref="confirm" />

    <DeleteErrorDialog
      :dialog="deleteErrorDialog"
      :errors="deleteErrors"
      :warnings="deleteWarnings"
      @okay="resetErrors"
    />

    <v-expansion-panels v-if="taskItems && taskItems.length > 0" accordion>
      <v-expansion-panel
        class="todo-list"
        v-for="(item, index) in orderBy(taskItems, 'order')"
        v-bind:key="index"
        expand-icon=""
        :class="{ 'disabled': !item.enabled, 'draft': isDraft(item) }">

        <v-expansion-panel-header class="no-dropdown">
          <div class="list-item">
            <div class="filing-type">
              <div class="list-item__title">{{item.title}}</div>
              <div class="list-item__subtitle">
                <div v-if="item.subtitle" class="todo-status">{{item.subtitle}}</div>

                <div v-if="isDraft(item)" class="todo-status">
                  DRAFT
                </div>

                <div v-else-if="isPending(item)" class="todo-status">
                  <div>FILING PENDING</div>
                  <div class="vert-pipe">&nbsp;</div>
                  <div class="payment-status" v-if="inProcessFiling !== undefined && inProcessFiling === item.id">
                    PROCESSING...
                  </div>
                  <div class="payment-status" v-else>
                    <span>PAYMENT INCOMPLETE</span>
                    <v-btn small icon color="black" class="info-btn"><v-icon>mdi-information-outline</v-icon></v-btn>
                  </div>
                </div>

                <div v-else-if="isError(item)" class="todo-status">
                  <div>FILING PENDING</div>
                  <div class="vert-pipe">&nbsp;</div>
                  <div class="payment-status" v-if="inProcessFiling !== undefined && inProcessFiling === item.id">
                    PROCESSING...
                  </div>
                  <div class="payment-status" v-else>
                    <span>PAYMENT UNSUCCESSFUL</span>
                    <v-btn small icon color="black" class="info-btn"><v-icon>mdi-information-outline</v-icon></v-btn>
                  </div>
                </div>

                <div v-else-if="isPaid(item)" class="todo-status">
                  <div>FILING PENDING</div>
                  <div class="vert-pipe">&nbsp;</div>
                  <div class="payment-status" v-if="inProcessFiling !== undefined && inProcessFiling === item.id">
                    PROCESSING...
                  </div>
                  <div class="payment-status" v-else>
                    <span>PAID</span>
                    <v-btn small icon color="black" class="info-btn"><v-icon>mdi-information-outline</v-icon></v-btn>
                  </div>
                </div>
              </div>
            </div>

            <div class="list-item__actions">
              <!-- pre-empt any buttons below -->
              <template v-if="inProcessFiling !== undefined && inProcessFiling === item.id">
                <v-btn text loading disabled />
              </template>

              <template v-else-if="isDraft(item)">
                <v-btn id="btn-draft-resume"
                  color="primary"
                  :disabled="!item.enabled"
                  @click.native.stop="doResumeFiling(item)"
                >
                  Resume
                </v-btn>
                <!-- more DRAFT actions menu -->
                <v-menu offset-y left>
                  <template v-slot:activator="{ on }">
                    <v-btn color="primary" class="actions__more-actions__btn px-0"
                      v-on="on" id="menu-activator" :disabled="!item.enabled"
                    >
                      <v-icon>mdi-menu-down</v-icon>
                    </v-btn>
                  </template>
                  <v-list ref="draft_actions" class="actions__more-actions">
                    <v-list-item id="btn-delete-draft" @click="confirmDeleteDraft(item)">
                      <v-list-item-title>Delete Draft</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </template>

              <v-btn v-else-if="isPending(item)"
                color="primary"
                :disabled="!item.enabled"
                @click.native.stop="doResumePayment(item)"
              >
                Resume Payment
              </v-btn>

              <v-btn v-else-if="isError(item)"
                color="primary"
                :disabled="!item.enabled"
                @click.native.stop="doResumePayment(item)"
              >
                Retry Payment
              </v-btn>

              <template v-else-if="isPaid(item)">
                <!-- no action button in this case -->
              </template>

              <v-btn v-else-if="!isCompleted(item)"
                color="primary"
                :disabled="!item.enabled"
                @click.native.stop="doFileNow(item)"
              >
                File Now
              </v-btn>
            </div>
          </div>
        </v-expansion-panel-header>

        <v-expansion-panel-content>
            <v-card v-if="isPending(item)">
              <v-card-text>
                <p class="font-weight-bold black--text">Payment Incomplete</P>
                <p>This filing is pending payment. The payment may still be in progress or may have been
                  interrupted for some reason.<p>
                <p>You may continue this filing by selecting "Resume Payment".</p>
              </v-card-text>
            </v-card>
            <v-card v-else-if="isError(item)">
              <v-card-text>
                <p class="font-weight-bold black--text">Payment Unsuccessful</p>
                <p>This filing is pending payment. The payment appears to have been unsuccessful for some
                  reason.</p>
                <p>You may continue this filing by selecting "Retry Payment".</p>
              </v-card-text>
            </v-card>
            <v-card v-else-if="isPaid(item)">
              <v-card-text>
                <p class="font-weight-bold black--text">Paid</p>
                <p>This filing is paid but the filing is not yet complete. Please check again later.</p>
              </v-card-text>
            </v-card>
        </v-expansion-panel-content>

      </v-expansion-panel>
    </v-expansion-panels>

    <!-- No Results Message -->
    <v-card class="no-results" flat v-if="taskItems && taskItems.length === 0">
      <v-card-text>
        <div class="no-results__title">You don't have anything to do yet</div>
        <div class="no-results__subtitle">Filings that require your attention will appear here</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import axios from '@/axios-auth'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ExternalMixin from '@/mixins/external-mixin'
import { mapState, mapActions } from 'vuex'
import DeleteErrorDialog from '@/components/Dashboard/DeleteErrorDialog'

export default {
  name: 'TodoList',

  components: {
    DeleteErrorDialog,
    ConfirmDialog
  },

  mixins: [ExternalMixin],

  data () {
    return {
      taskItems: null,
      deleteErrors: [],
      deleteWarnings: [],
      deleteErrorDialog: false
    }
  },

  props: {
    inProcessFiling: null
  },

  computed: {
    ...mapState(['tasks', 'entityIncNo'])
  },

  created () {
    // load data into this page
    this.loadData()
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setCurrentFilingStatus', 'setTriggerDashboardReload']),

    loadData () {
      this.taskItems = []

      // create task items
      this.tasks.forEach(task => {
        if (task && task.task && task.task.todo) {
          this.loadTodoItem(task)
        } else if (task && task.task && task.task.filing) {
          this.loadFilingItem(task)
        } else {
          console.log('ERROR - got unknown task =', task)
        }
      })

      this.$emit('todo-count', this.taskItems.length)
      this.$emit('todo-filings', this.taskItems)

      // If this is a draft/pending/error/paid item, emit the has-blocker-filings event to the parent component.
      // This indicates that a new filing cannot be started because this one has to be completed first.
      this.$emit('has-blocker-filing',
        this.taskItems.filter(elem => {
          return this.isDraft(elem) || this.isPending(elem) || this.isError(elem) || this.isPaid(elem)
        }).length > 0
      )
    },

    loadTodoItem (task) {
      const todo = task.task.todo
      if (todo && todo.header) {
        switch (todo.header.name) {
          case 'annualReport': {
            const ARFilingYear = todo.header.ARFilingYear
            this.taskItems.push({
              type: todo.header.name,
              title: `File ${ARFilingYear} Annual Report`,
              subtitle: task.enabled ? '(including Address and/or Director Change)' : null,
              ARFilingYear,
              status: todo.header.status || 'NEW',
              enabled: Boolean(task.enabled),
              order: task.order
            })
            break
          }
          default:
            console.log('ERROR - got unknown todo item =', todo)
            break
        }
      } else {
        console.log('ERROR - invalid todo or header in task =', task)
      }
    },

    loadFilingItem (task) {
      const filing = task.task.filing
      if (filing && filing.header) {
        switch (filing.header.name) {
          case 'annualReport':
            this.loadAnnualReport(task)
            break
          case 'changeOfDirectors':
            this.loadChangeOfDirectors(task)
            break
          case 'changeOfAddress':
            this.loadChangeOfAddress(task)
            break
          default:
            console.log('ERROR - got unknown filing item =', filing)
            break
        }
      } else {
        console.log('ERROR - invalid filing or header in task =', task)
      }
    },

    loadAnnualReport (task) {
      const filing = task.task.filing
      if (filing && filing.header && filing.annualReport) {
        const date = filing.annualReport.annualGeneralMeetingDate
        if (date) {
          const ARFilingYear = +date.substring(0, 4)
          this.taskItems.push({
            type: filing.header.name,
            id: filing.header.filingId,
            title: `File ${ARFilingYear} Annual Report`,
            draftTitle: `${ARFilingYear} Annual Report`,
            ARFilingYear,
            status: filing.header.status || 'NEW',
            enabled: Boolean(task.enabled),
            order: task.order,
            paymentToken: filing.header.paymentToken || null
          })
        } else {
          console.log('ERROR - invalid date in filing =', filing)
        }
      } else {
        console.log('ERROR - invalid filing or header or annualReport in task =', task)
      }
    },

    loadChangeOfDirectors (task) {
      const filing = task.task.filing
      if (filing && filing.header && filing.changeOfDirectors) {
        this.taskItems.push({
          type: filing.header.name,
          id: filing.header.filingId,
          title: `File Director Change`,
          draftTitle: `Director Change`,
          status: filing.header.status || 'NEW',
          enabled: Boolean(task.enabled),
          order: task.order,
          paymentToken: filing.header.paymentToken || null
        })
      } else {
        console.log('ERROR - invalid filing or header or changeOfDirectors in task =', task)
      }
    },

    loadChangeOfAddress (task) {
      const filing = task.task.filing
      if (filing && filing.header && filing.changeOfAddress) {
        this.taskItems.push({
          type: filing.header.name,
          id: filing.header.filingId,
          title: `File Address Change`,
          draftTitle: `Address Change`,
          status: filing.header.status || 'NEW',
          enabled: Boolean(task.enabled),
          order: task.order,
          paymentToken: filing.header.paymentToken || null
        })
      } else {
        console.log('ERROR - invalid filing or header or changeOfAddress in task =', task)
      }
    },

    doFileNow (item) {
      switch (item.type) {
        case 'annualReport':
          // file the subject Annual Report
          this.setARFilingYear(item.ARFilingYear)
          this.setCurrentFilingStatus('NEW')
          this.$router.push({ name: 'annual-report', params: { id: 0 } }) // 0 means "new AR"
          break
        default:
          console.log('doFileNow(), invalid type for item =', item)
      }
    },

    doResumeFiling (item) {
      switch (item.type) {
        case 'annualReport':
          // resume the subject Annual Report
          this.setARFilingYear(item.ARFilingYear)
          this.setCurrentFilingStatus('DRAFT')
          this.$router.push({ name: 'annual-report', params: { id: item.id } })
          break
        case 'changeOfDirectors':
          // resume the subject Change Of Directors
          this.setARFilingYear(item.ARFilingYear)
          this.setCurrentFilingStatus('DRAFT')
          this.$router.push({ name: 'standalone-directors', params: { id: item.id } })
          break
        case 'changeOfAddress':
          // resume the subject Change Of Address
          this.setARFilingYear(item.ARFilingYear)
          this.setCurrentFilingStatus('DRAFT')
          this.$router.push({ name: 'standalone-addresses', params: { id: item.id } })
          break
        default:
          console.log('doFileNow(), invalid type for item =', item)
      }
    },

    // this is called for both Resume Payment and Retry Payment
    doResumePayment (item) {
      const filingId = item.id
      const paymentToken = item.paymentToken

      const baseUrl = sessionStorage.getItem('BASE_URL')
      const returnURL = encodeURIComponent(baseUrl + 'dashboard?filing_id=' + filingId)
      const authUrl = sessionStorage.getItem('AUTH_URL')
      const payURL = authUrl + 'makepayment/' + paymentToken + '/' + returnURL

      // assume Pay URL is always reachable
      window.location.assign(payURL)
      return true
    },

    isNew (item) {
      return item.status === 'NEW'
    },

    isDraft (item) {
      return item.status === 'DRAFT'
    },

    isPending (item) {
      return item.status === 'PENDING'
    },

    isError (item) {
      return item.status === 'ERROR'
    },

    isPaid (item) {
      return item.status === 'PAID'
    },

    isCompleted (item) {
      return item.status === 'COMPLETED'
    },

    confirmDeleteDraft (item) {
      // open confirmation dialog and wait for response
      this.$refs.confirm.open(
        'Delete Draft?',
        'Delete your ' + item.draftTitle + '? Any changes you\'ve made will be lost.',
        {
          width: '40rem',
          persistent: true,
          yes: 'Delete',
          no: null,
          cancel: 'Don\'t delete'
        }
      ).then(async (confirm) => {
        // if we get here, Yes or No was clicked
        if (confirm) {
          await this.doDeleteDraft(item)
        } else {
          // do nothing
        }
      }).catch(() => {
        // if we get here, Cancel was clicked - do nothing
      })
    },

    async doDeleteDraft (item) {
      let url = this.entityIncNo + '/filings/' + item.id
      await axios.delete(url).then(res => {
        if (!res) { throw new Error('invalid API response') }

        // reload dashboard
        this.setTriggerDashboardReload(true)
      }).catch(error => {
        if (error && error.response) {
          if (error.response.data.errors) {
            this.deleteErrors = error.response.data.errors
          }
          if (error.response.data.warnings) {
            this.deleteWarnings = error.response.data.warnings
          }
          this.deleteErrorDialog = true
        } else {
          this.deleteErrorDialog = true
        }
      })
    },

    resetErrors () {
      this.deleteErrorDialog = false
      this.deleteErrors = []
      this.deleteWarnings = []
    }
  },

  watch: {
    tasks () {
      // if tasks changes, reload them
      // (does not fire on initial page load)
      this.loadData()
    }
  }
}
</script>

<style lang="scss" scoped>
@import "@/assets/styles/theme.scss";

.todo-list {
  // disable expansion
  pointer-events: none;
}

.todo-list.disabled {
  opacity: 0.6;

  .info-btn {
    // enable expansion button
    pointer-events: auto;
  }
}

.todo-list:not(.disabled) {
  .v-btn {
    // enable action buttons
    pointer-events: auto;
  }
}

.todo-list.draft .v-expansion-panel-content {
  display: none;
}

.todo-list .list-item {
  padding: 0;
  justify-content: space-evenly;
}

.todo-list .list-item .list-item__actions {
  #btn-draft-resume {
    min-width: 103px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
  }
}

.list-item__actions .v-btn.actions__more-actions__btn {
  min-width: 38px !important;
  width: 38px;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  margin-left: 1px;
}

.actions__more-actions {
  padding: 0;
}

.filing-type {
  flex: 1 1 auto;
}

.info-btn {
  margin-left: 0.25rem;
}

.todo-status {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.payment-status {
  display: flex;
  align-items: center;
  height: 28px; // for consistent height with and without icon button
}

.vert-pipe {
  margin-top: 0.1rem;
  margin-left: 0.75rem;
  margin-right: 0.75rem;
  height: 1rem;
  border-left: 1px solid $gray6
}

</style>
