import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import VueRouter from 'vue-router'
import sinon from 'sinon'
import { createLocalVue, shallowMount } from '@vue/test-utils'

import axios from '@/axios-auth'
import store from '@/store/store'
import App from '@/App.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('App', () => {
  // just need a token that can get parsed properly (will be expired but doesn't matter for tests)
  sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3' +
    'FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiJlMmJlNDc5Yi0zYTkzLTRhNjAtYmZhNi1hZjM4MWE2YTBmNGMiLCJleHA' +
    'iOjE1Njc4ODQ4NjMsIm5iZiI6MCwiaWF0IjoxNTY3Nzk4NDYzLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2Ev' +
    'YXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiIwMmNiNjhiNC00M2UyLTRmYmEtY' +
    'TI2Yi1hZWNiMGRhOTlhYzciLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdG' +
    'UiOiI5NGU2N2ZjNy0xMDg3LTRmZjItYTNlOC1mMWU5ZjkzMzIxNjciLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTI' +
    'uMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJy' +
    'b2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiY' +
    'WNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcG' +
    'UiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2V' +
    'ybmFtZSI6ImNwMDAwMTM2NCIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTM2NCJ9.VfTdZ2ZnZyUjkFiztA8' +
    'LRkaijPbHAddm0QmMGgEIDv9Z3EGHaYtTs2L3cSH_bYdUjjclwGwt0GIz3DOHviS8yXuwkzRVHI8W3mdY1dionkqU26_miA10Yxl1ZnFmQpZc' +
    'MHmS4dMcb-_CU6ysgemiO8wonalqLb7Lz01Zd1h2NCyTC4Twk3BFuZNHlXiaXWVaF2UgtQI1Gf7XfRCPQhdLLYPt6mzL_nEnRveCOdqXVM6XK' +
    'OPjpHUIMONexFGbojmRsCg5w-qQrXYY8m-lA17GLdlCCAtrJXlS0mLbFr1jQL0eroqtrFm9WoQByVaso5Kx_n7wXx4h3BjunSJuqsJCmA')
  sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001364')

  let wrapper
  let vm

  beforeEach(done => {
    const get = sinon.stub(axios, 'get')

    // GET authorizations (role)
    get.withArgs('CP0001364/authorizations')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            role: 'OWNER'
          }
      })))

    // GET entity info
    // NB: contains responses for 2 axios calls with the same signature
    get.withArgs('CP0001364')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            // Auth API Entity data
            contacts: [
              {
                email: 'name@mail.com',
                phone: '(123)-456-7890'
              }
            ],
            // Legal API Business data
            business: {
              legalName: 'TEST NAME',
              status: 'GOODSTANDING',
              taxId: '123456789',
              identifier: 'CP0001364',
              lastLedgerTimestamp: '2019-08-14T22:27:12+00:00',
              foundingDate: '2000-07-13T00:00:00+00:00',
              lastAnnualGeneralMeetingDate: '2019-08-16'
            }
          }
      })))

    // GET tasks
    get.withArgs('CP0001364/tasks')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'tasks': [
              {
                'task': {
                  'todo': {
                    'header': {
                      'name': 'annualReport',
                      'ARFilingYear': 2017,
                      'status': 'NEW'
                    }
                  }
                },
                'enabled': true,
                'order': 1
              },
              {
                'task': {
                  'todo': {
                    'header': {
                      'name': 'annualReport',
                      'ARFilingYear': 2018,
                      'status': 'NEW'
                    }
                  }
                },
                'enabled': false,
                'order': 2
              },
              {
                'task': {
                  'todo': {
                    'header': {
                      'name': 'annualReport',
                      'ARFilingYear': 2019,
                      'status': 'NEW'
                    }
                  }
                },
                'enabled': false,
                'order': 3
              }
            ]
          }
      })))

    // GET filings
    get.withArgs('CP0001364/filings')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filings': [
              {
                'filing': {
                  'header': {
                    'name': 'annualReport',
                    'date': '2019-01-02',
                    'paymentToken': 123,
                    'certifiedBy': 'Full Name 1',
                    'filingId': 321
                  },
                  'annualReport': {
                    'annualGeneralMeetingDate': '2019-12-31'
                  }
                }
              },
              {
                'filing': {
                  'header': {
                    'name': 'changeOfDirectors',
                    'date': '2019-03-04',
                    'paymentToken': 456,
                    'certifiedBy': 'Full Name 2',
                    'filingId': 654
                  },
                  'changeOfDirectors': {
                  }
                }
              },
              {
                'filing': {
                  'header': {
                    'name': 'changeOfAddress',
                    'date': '2019-05-06',
                    'paymentToken': 789,
                    'certifiedBy': 'Full Name 3',
                    'filingId': 987
                  },
                  'changeOfAddress': {
                  }
                }
              }
            ]
          }
      })))

    // GET addresses
    get.withArgs('CP0001364/addresses')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'mailingAddress': {
              'streetAddress': '1012 Douglas St',
              'addressCity': 'Victoria',
              'addressRegion': 'BC',
              'postalCode': 'V8W 2C3',
              'addressCountry': 'CA'
            },
            'deliveryAddress': {
              'streetAddress': '220 Buchanan St',
              'addressCity': 'Glasgow',
              'addressRegion': 'Scotland',
              'postalCode': 'G1 2FFF',
              'addressCountry': 'UK'
            }
          }
      })))

    // GET directors
    get.withArgs('CP0001364/directors')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            directors: [
              {
                'officer': {
                  'firstName': 'Peter',
                  'lastName': 'Griffin'
                },
                'deliveryAddress': {
                  'streetAddress': '1012 Douglas St',
                  'addressCity': 'Victoria',
                  'addressRegion': 'BC',
                  'postalCode': 'V8W 2C3',
                  'addressCountry': 'CA'
                }
              },
              {
                'officer': {
                  'firstName': 'Joe',
                  'lastName': 'Swanson'
                },
                'deliveryAddress': {
                  'streetAddress': '220 Buchanan St',
                  'addressCity': 'Glasgow',
                  'addressRegion': 'Scotland',
                  'postalCode': 'G1 2FFF',
                  'addressCountry': 'UK'
                }
              }
            ]
          }
      })))

    // create a Local Vue and install router (and store) on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = new VueRouter()
    wrapper = shallowMount(App, { localVue, router, store })
    vm = wrapper.vm

    vm.$nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('fetches Role properly', () => {
    expect(vm.$store.state.role).toBe('OWNER')
    expect(vm.$store.getters.isRoleOwner).toBe(true)
    expect(vm.$store.getters.isRoleAdmin).toBe(false)
    expect(vm.$store.getters.isRoleMember).toBe(false)
    expect(vm.$store.getters.isRoleStaff).toBe(false)
  })

  it('fetches Business Info properly', () => {
    expect(vm.$store.state.businessEmail).toEqual('name@mail.com')
    expect(vm.$store.state.businessPhone).toEqual('(123)-456-7890')
  })

  it('initializes Current Date properly', () => {
    const today = new Date()
    const year = today.getFullYear().toString()
    const month = (today.getMonth() + 1).toString().padStart(2, '0')
    const date = today.getDate().toString().padStart(2, '0')
    const currentDate = `${year}-${month}-${date}`
    expect(vm.$store.state.currentDate).toEqual(currentDate)
  })

  it('fetches Entity Info properly', () => {
    expect(vm.$store.state.entityName).toBe('TEST NAME')
    expect(vm.$store.state.entityStatus).toBe('GOODSTANDING')
    expect(vm.$store.state.entityBusinessNo).toBe('123456789')
    expect(vm.$store.state.entityIncNo).toBe('CP0001364')
    expect(vm.$store.state.lastPreLoadFilingDate).toBe('2019-08-14')
    expect(vm.$store.state.entityFoundingDate).toBe('2000-07-13')
    expect(vm.$store.state.lastAgmDate).toBe('2019-08-16')
  })

  it('fetches Tasks properly', () => {
    expect(vm.$store.state.tasks.length).toBe(3)
    expect(vm.$store.state.tasks[0].task.todo.header.ARFilingYear).toBe(2017)
    expect(vm.$store.state.tasks[1].task.todo.header.ARFilingYear).toBe(2018)
    expect(vm.$store.state.tasks[2].task.todo.header.ARFilingYear).toBe(2019)
  })

  it('fetches Filings properly', () => {
    expect(vm.$store.state.filings.length).toBe(3)
    expect(vm.$store.state.filings[0].filing.header.name).toBe('annualReport')
    expect(vm.$store.state.filings[1].filing.header.name).toBe('changeOfDirectors')
    expect(vm.$store.state.filings[2].filing.header.name).toBe('changeOfAddress')
  })

  it('fetches Addresses properly', () => {
    expect(vm.$store.state.mailingAddress.addressCity).toBe('Victoria')
    expect(vm.$store.state.deliveryAddress.addressCity).toBe('Glasgow')
  })

  it('fetches Directors properly', () => {
    expect(vm.$store.state.directors.length).toBe(2)
    expect(vm.$store.state.directors[0].officer.lastName).toBe('Griffin')
    expect(vm.$store.state.directors[1].officer.lastName).toBe('Swanson')
  })
})
