<template>
  <div v-if="todoItems">
    <v-card flat>
      <ul class="list todo-list">
        <li class="list-item"
          v-for="(item, index) in todoItems"
          v-bind:key="index">
          <div class="list-item-title">
            {{item.name}}
            <v-chip class="todo-status" label small disabled text-color="white"
              :class="{
                'green' : isNew(item),
                'blue' : isDraft(item),
                'grey' : isPending(item),
                'red' : isPayError(item)
              }">
              <span v-show="isNew(item)">NEW</span>
              <span v-show="isDraft(item)">DRAFT</span>
              <span v-show="isPending(item)">PENDING</span>
              <span v-show="isPayError(item)">PAY ERROR</span>
            </v-chip>
          </div>
          <div class="list-item-actions">
            <!-- NB: disable all items except the first one -->
            <v-btn color="primary" v-if="isNew(item)" :disabled="index > 0" @click="doFile(item)">
              File &amp; Pay
            </v-btn>
            <v-btn color="primary" v-if="isDraft(item)" :disabled="index > 0" @click="doResume(item)">
              Resume
            </v-btn>
            <v-btn color="primary" v-if="isPending(item)" :disabled="index > 0" @click="doCheckStatus(item)">
              Check Status
            </v-btn>
            <v-btn color="primary" v-if="isPayError(item)" :disabled="index > 0" @click="doRetryPayment(item)">
              Retry Payment
            </v-btn>
          </div>
        </li>
      </ul>
    </v-card>

     <!-- No Results Message -->
    <v-card class="no-results" flat v-if="todoItems.length === 0">
      <v-card-text>
        <div class="no-results__title">You don't have anything to do yet</div>
        <div class="no-results__subtitle">Filings that require your attention will appear here</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import Vue2Filters from 'vue2-filters'
import axios from '@/axios-auth'
import { mapState, mapActions } from 'vuex'
import { isEmpty } from 'lodash'

export default {
  name: 'TodoList',

  mixins: [Vue2Filters.mixin],

  data () {
    return {
      todoItems: null
    }
  },

  computed: {
    ...mapState(['corpNum'])
  },

  mounted () {
    // reload data for this page
    this.getTodoItems()
  },

  methods: {
    ...mapActions(['setARFilingYear', 'setCurrentARStatus', 'setRegOffAddrChange', 'setAgmDate',
      'setFiledDate', 'setNoAGM', 'setValidated']),

    getTodoItems () {
      this.todoItems = []
      if (this.corpNum) {
        const url = this.corpNum + '/filings' // TODO - add URL param to get only todo items
        axios.get(url).then(response => {
          if (response && response.data && response.data.filings) {
            // sort by id ascending (ie, earliest to latest)
            const filings = response.data.filings.sort(
              (a, b) => (a.filing.header.filingId - b.filing.header.filingId)
            )
            // create todo items
            // for (let i = 0; i < filings.length; i++) {
            //   const filing = response.data.filings[i].filing
            //   if (!isEmpty(filing.annualReport)) {
            //     this.todoItems.push({ /* TODO */ })
            //   } else if (!isEmpty(filing.directorChange)) {
            //     this.todoItems.push({ /* TODO */ })
            //   } else if (!isEmpty(filing.addressChange)) {
            //     this.todoItems.push({ /* TODO */ })
            //   }
            // }

            // sample Draft filing
            // -> we have a filing
            // -> we don't have an invoice
            this.todoItems.push({
              type: 'AR',
              name: `File 2018 Annual Report`,
              year: 2018,
              filing: { invoice: null }
            })

            // sample New filing
            // -> we don't have a filing
            this.todoItems.push({
              type: 'AR',
              name: `File 2019 Annual Report`,
              year: 2019,
              filing: null
            })

            // sample Pending filing
            // -> we have a filing
            // -> we have an invoice
            // -> we don't have a paid status
            this.todoItems.push({
              type: 'COA',
              name: `File Change Of Addresses`,
              filing: { invoice: { paid: null } }
            })

            // sample Pay Error filing
            // -> we have a filing
            // -> we have an invoice
            // -> we have a paid status error
            this.todoItems.push({
              type: 'COD',
              name: `File Change of Directors`,
              filing: { invoice: { paid: { error: true } } }
            })
          } else {
            console.log('getTodoItems() error - invalid Filings')
          }
          this.$emit('todo-count', this.todoItems.length)
        }).catch(error => console.error('getTodoItems() error =', error))
      }
    },
    doFile (item) {
      switch (item.type) {
        case 'AR':
          // file the subject Annual Report
          this.resetStore(item)
          this.$router.push('/annual-report')
          break
        case 'COA':
          // TODO - file the subject Change Of Address
          break
        case 'COD':
          // TODO - file the subject Change of Directors
          break
        default:
          console.log('doFile(), invalid type for item =', item)
      }
    },
    doResume (item) {
      // TODO
      this.doFile(item) // for now...
    },
    doCheckStatus (item) {
      // TODO
    },
    doPay (item) {
      switch (item.type) {
        case 'AR':
          // TODO - pay the subject Annual Report
          console.log('doPay(), type = AR, item =', item)
          break
        case 'COA':
          // TODO - pay the subject Change Of Address
          console.log('doPay(), type = COA, item =', item)
          break
        case 'COD':
          // TODO - pay the subject Change Of Directors
          console.log('doPay(), type = COD, item =', item)
          break
        default:
          console.log('doPay(), invalid type for item =', item)
      }
    },
    resetStore (item) {
      this.setARFilingYear(item.year)
      this.setCurrentARStatus('TODO')
      this.setRegOffAddrChange(false)
      this.setAgmDate(null)
      this.setFiledDate(null)
      this.setNoAGM(false)
      this.setValidated(false)
    },
    doRetryPayment (item) {
      // TODO
    },
    isNew (item) {
      return !item.filing
    },
    isDraft (item) {
      return item.filing && !item.filing.invoice
    },
    isPending (item) {
      return item.filing && item.filing.invoice && !item.filing.invoice.paid
    },
    isPayError (item) {
      return item.filing && item.filing.invoice && item.filing.invoice.paid && item.filing.invoice.paid.error
    }

  },

  watch: {
    corpNum (val) {
      // when Corp Num is set or changes, get new todo items
      this.getTodoItems()
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../../assets/styles/theme.styl"
</style>
