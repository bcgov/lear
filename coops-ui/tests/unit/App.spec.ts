import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import VueRouter from 'vue-router'
import sinon from 'sinon'
import { createLocalVue, shallowMount } from '@vue/test-utils'

import axios from '@/axios-auth'
import store from '@/store/store'
import App from '@/App.vue'
import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

describe('App', () => {
  // just need a token that can get parsed properly (will be expired but doesn't matter for tests)
  // must not include keycloakRoles=["staff"]
  sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3' +
    'FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIzZDQ3YjgwYy01MTAzLTRjMTYtOGNhZC0yMjU4NDMwZGYwZTciLCJleHA' +
    'iOjE1Njg0ODk1NTksIm5iZiI6MCwiaWF0IjoxNTY4NDAzMTYwLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2Ev' +
    'YXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwicmVhbG0tbWFuYWdlbWVudCIsImJyb2tlciIsImFjY291bnQiX' +
    'Swic3ViIjoiZDRjNTBiZTAtYWM2OC00MDIyLTkxMGQtMzE2NzQ4NGFkOWU0IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoic2JjLWF1dGgtd2ViIi' +
    'wibm9uY2UiOiJkMjljZTZlNS0xNzZhLTRkMTUtODUzZS05NWUzZmUwZmYwZjgiLCJhdXRoX3RpbWUiOjE1Njg0MDMxNTksInNlc3Npb25fc3R' +
    'hdGUiOiJiOTEwMzQxZi0xNzVjLTRkMTktYWI1Yy1iM2QxNTBiYjk0NjYiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8x' +
    'OTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6e' +
    'yJyb2xlcyI6WyJ2aWV3IiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwic3RhZmYiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZX' +
    'NvdXJjZV9hY2Nlc3MiOnsicmVhbG0tbWFuYWdlbWVudCI6eyJyb2xlcyI6WyJ2aWV3LWlkZW50aXR5LXByb3ZpZGVycyIsInZpZXctcmVhbG0' +
    'iLCJtYW5hZ2UtaWRlbnRpdHktcHJvdmlkZXJzIiwiaW1wZXJzb25hdGlvbiIsInJlYWxtLWFkbWluIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFn' +
    'ZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZ' +
    'S1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaX' +
    'phdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJicm9rZXIiOnsicm9sZXMiOlsicmVhZC10b2tlbiJdfSwiYWNjb3V' +
    'udCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJv' +
    'cGVuaWQiLCJmaXJzdG5hbWUiOiJTdW1lc2giLCJyb2xlcyI6WyJ2aWV3IiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwic3RhZmYiLCJ1bWFfY' +
    'XV0aG9yaXphdGlvbiIsImJhc2ljIl0sIm5hbWUiOiJTdW1lc2ggS2FyaXlpbCIsInByZWZlcnJlZF91c2VybmFtZSI6InNrYXJpeWlsQGlkaX' +
    'IiLCJlbWFpbCI6InN1bWVzaC5wLmthcml5aWxAZ292LmJjLmNhIiwibGFzdG5hbWUiOiJLYXJpeWlsIiwidXNlcm5hbWUiOiJza2FyaXlpbEB' +
    'pZGlyIn0.MSPSakOnCUia4qd-fUpvP2PB3k977Eyhjxn-ykjadsUTEK4f2R3c8vozxaIIMH0-qUwduyQmdZCl3tQnXYQ9Ttf1PE9eMLS4sXJi' +
    'IUlDmKZ2ow7GmmDabic8igHnEDYD6sI7OFYnCJhRdgVEHN-_4KUk2YsAVl5XUr6blJKMuYDPeMyNreGTXU7foE4AT-93FwlyTyFzQGddrDvc6' +
    'kkQr7mgJNTtgg87DdYbVGbEtIetyVfvwEF0rU8JH2N-j36XIebo33FU3-gJ5Y5S69EHPqQ37R9H4d8WUrHO-4QzJQih3Yaea820XBplJeo0DO' +
    '3hQoVtPD42j0p3aIy10cnW2g')
  sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001867')

  let wrapper
  let vm

  beforeEach(done => {
    const get = sinon.stub(axios, 'get')

    // GET authorizations (role)
    get.withArgs('CP0001867/authorizations')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            roles: ['edit', 'view']
          }
      })))

    // GET entity info
    // NB: contains responses for 2 axios calls with the same signature
    get.withArgs('CP0001867')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            // Auth API Entity data
            contacts: [
              {
                email: 'name@mail.com',
                phone: '(111)-222-3333',
                phoneExtension: '999'
              }
            ],
            // Legal API Business data
            business: {
              legalName: 'TEST NAME',
              status: 'GOODSTANDING',
              taxId: '123456789',
              identifier: 'CP0001867',
              lastLedgerTimestamp: '2019-08-14T22:27:12+00:00',
              foundingDate: '2000-07-13T00:00:00+00:00',
              lastAnnualGeneralMeetingDate: '2019-08-16',
              legalType: null
            }
          }
      })))

    // GET tasks
    get.withArgs('CP0001867/tasks')
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
    get.withArgs('CP0001867/filings')
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
    get.withArgs('CP0001867/addresses')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'registeredOffice':
              {
                'mailingAddress': {
                  'streetAddress': '1012 Douglas St',
                  'addressCity': 'Victoria',
                  'addressRegion': 'BC',
                  'addressType': 'mailing',
                  'postalCode': 'V8W 2C3',
                  'addressCountry': 'CA'
                },
                'deliveryAddress': {
                  'streetAddress': '220 Buchanan St',
                  'addressCity': 'Glasgow',
                  'addressRegion': 'Scotland',
                  'addressType': 'delivery',
                  'postalCode': 'G1 2FFF',
                  'addressCountry': 'UK'
                }
              },
            'recordsOffice':
              {
                'mailingAddress': {
                  'streetAddress': '1012 Douglas St',
                  'addressCity': 'Vancouver',
                  'addressRegion': 'BC',
                  'addressType': 'mailing',
                  'postalCode': 'V8W 2C3',
                  'addressCountry': 'CA'
                },
                'deliveryAddress': {
                  'streetAddress': '220 Buchanan St',
                  'addressCity': 'Glasgow',
                  'addressRegion': 'Scotland',
                  'addressType': 'delivery',
                  'postalCode': 'G1 2FFF',
                  'addressCountry': 'UK'
                }
              }
          }
      })))

    // GET directors
    get.withArgs('CP0001867/directors')
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
    wrapper = shallowMount(App, { localVue, router, store, vuetify })
    vm = wrapper.vm

    vm.$nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('gets Keycloak Roles and Auth Roles properly', () => {
    expect(vm.$store.getters.isRoleStaff).toBe(true)
    expect(vm.$store.getters.isRoleEdit).toBe(true)
    expect(vm.$store.getters.isRoleView).toBe(true)
  })

  it('fetches Business Info properly', () => {
    expect(vm.$store.state.businessEmail).toEqual('name@mail.com')
    expect(vm.$store.state.businessPhone).toEqual('(111)-222-3333')
    expect(vm.$store.state.businessPhoneExtension).toEqual('999')
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
    expect(vm.$store.state.entityIncNo).toBe('CP0001867')
    expect(vm.$store.state.lastPreLoadFilingDate).toBe('2019-08-14')
    expect(vm.$store.state.entityFoundingDate).toBe('2000-07-13T00:00:00+00:00')
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
    expect(vm.$store.state.registeredAddress.mailingAddress.addressCity).toBe('Victoria')
    expect(vm.$store.state.registeredAddress.deliveryAddress.addressCity).toBe('Glasgow')

    expect(vm.$store.state.recordsAddress.mailingAddress.addressCity).toBe('Vancouver')
    expect(vm.$store.state.recordsAddress.deliveryAddress.addressCity).toBe('Glasgow')

    // These values have been assigned in the mockResponse but are expected to be filtered out by front-end logic.
    expect(vm.$store.state.registeredAddress.addressType).toBeUndefined()
    expect(vm.$store.state.recordsAddress.addressType).toBeUndefined()
  })

  it('fetches Directors properly', () => {
    expect(vm.$store.state.directors.length).toBe(2)
    expect(vm.$store.state.directors[0].officer.lastName).toBe('Griffin')
    expect(vm.$store.state.directors[1].officer.lastName).toBe('Swanson')
  })
})
