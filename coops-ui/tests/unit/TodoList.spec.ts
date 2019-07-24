import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import TodoList from '@/components/Dashboard/TodoList.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('TodoList.vue', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.currentDate = '2019-07-12'
    store.state.lastAgmDate = '2017-04-08'

    // GET tasks
    // NB: we would never receive this kind of data
    //     (draft + new + payment incomplete + payment unsucessful)
    sinon.stub(axios, 'get').withArgs('CP0001191/tasks')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'tasks': [
              {
                'task': {
                  'filing': {
                    'annualReport': {
                      'annualGeneralMeetingDate': '2018-07-15',
                      'certifiedBy': 'full1 name1',
                      'email': 'no_one@never.get'
                    },
                    'changeOfAddress': {
                      'certifiedBy': 'full2 name2',
                      'email': 'no_one@never.get'
                    },
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
                      'filingId': 123,
                      'name': 'annualReport',
                      'status': 'DRAFT'
                    }
                  }
                },
                'order': 2,
                'enabled': false
              },
              {
                'task': {
                  'todo': {
                    'business': {
                      'cacheId': 1,
                      'foundingDate': '2007-04-08',
                      'identifier': 'CP0002098',
                      'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                      'legalName': 'Legal Name - CP0002098'
                    },
                    'header': {
                      'name': 'annualReport',
                      'ARFilingYear': 2019,
                      'status': 'NEW'
                    }
                  }
                },
                'order': 1,
                'enabled': true
              },
              {
                'task': {
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
                'order': 4,
                'enabled': false
              },
              {
                'task': {
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
                },
                'order': 3,
                'enabled': false
              }
            ]
          }
      })))

    const constructor = Vue.extend(TodoList)
    const instance = new constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('loads and displays the Task Items properly', () => {
    expect(vm.taskItems).not.toBeNull()
    expect(vm.taskItems.length).toEqual(4)
  })

  it('loads the Draft task properly', () => {
    // TODO:
    // find first item
    // expect title to be "File 2019 Annual Report"
    // expect subtitle to be "(including Address and/or Director Change)"
    // expect status1 to be null
    // expect status2 to be null
    // expect button to be "File Now"
    // expect button to be enabled
  })

  it('loads the New task properly', () => {
    // TODO:
    // find second item
    // expect title to be "File 2018 Annual Report"
    // expect subtitle to be null
    // expect status1 to be "DRAFT"
    // expect status2 to be null
    // expect button to be "Resume"
    // expect button to be disabled
  })

  it('loads the Filing Pending - Payment Incomplete task properly', () => {
    // TODO:
    // find third item
    // expect title to be "File Director Change"
    // expect subtitle to be null
    // expect status1 to be "FILING PENDING"
    // expect status2 to be "PAYMENT INCOMPLETE"
    // expect status2 button to be enabled
    // expect button to be "Resume Payment"
    // expect button to be disabled
  })

  it('loads the Filing Pending - Payment Unsuccessful task properly', () => {
    // TODO:
    // find fourth item
    // expect title to be "File Address Change"
    // expect subtitle to be null
    // expect status1 to be "FILING PENDING"
    // expect status2 to be "PAYMENT UNSUCCESSFUL"
    // expect status2 button to be enabled
    // expect button to be "Retry Payment"
    // expect button to be disabled
  })
})
