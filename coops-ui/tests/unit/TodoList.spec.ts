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

  it('loads the \'New\' task properly', () => {
    // find first item
    const item = vm.$el.querySelectorAll('.list-item')[0]

    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent).toBe('(including Address and/or Director Change)')
    expect(item.querySelector('.list-item__status1')).toBeNull()
    expect(item.querySelector('.list-item__status2')).toBeNull()

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toEqual('File Now')
  })

  it('loads the \'Draft\' task properly', () => {
    // find second item
    const item = vm.$el.querySelectorAll('.list-item')[1]

    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2018 Annual Report')
    expect(item.querySelector('.list-item__subtitle')).toBeNull()
    expect(item.querySelector('.list-item__status1').textContent).toContain('DRAFT')
    expect(item.querySelector('.list-item__status2').textContent).toEqual('')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(true)
    expect(button.querySelector('.v-btn__content').textContent).toEqual('Resume')
  })

  it('loads the \'Filing Pending - Payment Incomplete\' task properly', () => {
    // find third item
    const item = vm.$el.querySelectorAll('.list-item')[2]

    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle')).toBeNull()
    expect(item.querySelector('.list-item__status1').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__status2').textContent).toContain('PAYMENT INCOMPLETE')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(true)
    expect(button.querySelector('.v-btn__content').textContent).toEqual('Resume Payment')
  })

  it('loads the \'Filing Pending - Payment Unsuccessful\' task properly', () => {
    // find fourth item
    const item = vm.$el.querySelectorAll('.list-item')[3]

    expect(item.querySelector('.list-item__title').textContent).toEqual('File Address Change')
    expect(item.querySelector('.list-item__subtitle')).toBeNull()
    expect(item.querySelector('.list-item__status1').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__status2').textContent).toContain('PAYMENT UNSUCCESSFUL')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(true)
    expect(button.querySelector('.v-btn__content').textContent).toEqual('Retry Payment')
  })
})
