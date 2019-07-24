import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import FilingHistoryList from '@/components/Dashboard/FilingHistoryList.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('FilingHistoryList.vue', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'

    // GET filing history
    sinon.stub(axios, 'get').withArgs('CP0001191/filings')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filings': [
              {
                'filing': {
                  'annualReport': {
                    'annualGeneralMeetingDate': '2018-07-15',
                    'certifiedBy': 'full1 name1',
                    'email': 'no_one@never.get'
                  },
                  'business': {
                    'cacheId': 1,
                    'foundingDate': '2007-04-08',
                    'identifier': 'CP0002098',
                    'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                    'legalName': 'Legal Name - CP0002098'
                  },
                  'header': {
                    'date': '2017-06-06',
                    'filingId': 123,
                    'name': 'annualReport',
                    'status': 'DRAFT'
                  }
                }
              },
              {
                'filing': {
                  'changeOfAddress': {
                    'certifiedBy': 'full2 name2',
                    'email': 'no_one@never.get'
                  },
                  'business': {
                    'cacheId': 1,
                    'foundingDate': '2007-04-08',
                    'identifier': 'CP0002098',
                    'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                    'legalName': 'Legal Name - CP0002098'
                  },
                  'header': {
                    'date': '2017-06-06',
                    'filingId': 456,
                    'name': 'changeOfAddress',
                    'status': 'ERROR'
                  }
                }
              },
              {
                'filing': {
                  'changeOfDirectors': {
                    'certifiedBy': 'full3 name3',
                    'email': 'no_one@never.get'
                  },
                  'business': {
                    'cacheId': 1,
                    'foundingDate': '2007-04-08',
                    'identifier': 'CP0002098',
                    'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                    'legalName': 'Legal Name - CP0002098'
                  },
                  'header': {
                    'date': '2017-06-06',
                    'filingId': 789,
                    'name': 'changeOfDirectors',
                    'status': 'PENDING'
                  }
                }
              }
            ]
          }
      })))

    const constructor = Vue.extend(FilingHistoryList)
    const instance = new constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('loads and displays the Filed Items properly', () => {
    expect(vm.filedItems).not.toBeNull()
    expect(vm.filedItems.length).toEqual(3)
  })
})
