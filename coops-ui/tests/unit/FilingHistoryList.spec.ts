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
                    'annualGeneralMeetingDate': '2017-04-08',
                    'certifiedBy': 'full name'
                  },
                  'header': {
                    'date': '2017-06-06',
                    'filingId': 3,
                    'status': 'COMPLETE'
                  }
                }
              },
              {
                'filing': {
                  'annualReport': {
                    'annualGeneralMeetingDate': '2015-04-08',
                    'certifiedBy': 'full name'
                  },
                  'header': {
                    'date': '2015-06-06',
                    'filingId': 1,
                    'status': 'PENDING'
                  }
                }
              },
              {
                'filing': {
                  'annualReport': {
                    'annualGeneralMeetingDate': '2016-04-08',
                    'certifiedBy': 'full name'
                  },
                  'header': {
                    'date': '2016-06-06',
                    'filingId': 2,
                    'status': 'COMPLETE'
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
