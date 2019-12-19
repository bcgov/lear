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

let vuetify = new Vuetify({})

describe('App as a COOP', () => {
  let wrapper
  let vm

  beforeEach(done => {
    // we need a token that can get parsed properly (will be expired but doesn't matter for tests)
    // must not include keycloakRoles=["staff"]
    sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3' +
        'FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIzZDQ3YjgwYy01MTAzLTRjMTYtOGNhZC0yMjU4NDMwZGYwZTciLCJle' +
      'HAiOjE1Njg0ODk1NTksIm5iZiI6MCwiaWF0IjoxNTY4NDAzMTYwLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2' +
      'EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwicmVhbG0tbWFuYWdlbWVudCIsImJyb2tlciIsImFjY291bnQ' +
      'iXSwic3ViIjoiZDRjNTBiZTAtYWM2OC00MDIyLTkxMGQtMzE2NzQ4NGFkOWU0IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoic2JjLWF1dGgtd2Vi' +
      'Iiwibm9uY2UiOiJkMjljZTZlNS0xNzZhLTRkMTUtODUzZS05NWUzZmUwZmYwZjgiLCJhdXRoX3RpbWUiOjE1Njg0MDMxNTksInNlc3Npb25fc' +
      '3RhdGUiOiJiOTEwMzQxZi0xNzVjLTRkMTktYWI1Yy1iM2QxNTBiYjk0NjYiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly' +
      '8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI' +
      '6eyJyb2xlcyI6WyJ2aWV3IiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwic3RhZmYiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJy' +
      'ZXNvdXJjZV9hY2Nlc3MiOnsicmVhbG0tbWFuYWdlbWVudCI6eyJyb2xlcyI6WyJ2aWV3LWlkZW50aXR5LXByb3ZpZGVycyIsInZpZXctcmVhb' +
      'G0iLCJtYW5hZ2UtaWRlbnRpdHktcHJvdmlkZXJzIiwiaW1wZXJzb25hdGlvbiIsInJlYWxtLWFkbWluIiwiY3JlYXRlLWNsaWVudCIsIm1hbm' +
      'FnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmF' +
      'nZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9y' +
      'aXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJicm9rZXIiOnsicm9sZXMiOlsicmVhZC10b2tlbiJdfSwiYWNjb' +
      '3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOi' +
      'JvcGVuaWQiLCJmaXJzdG5hbWUiOiJTdW1lc2giLCJyb2xlcyI6WyJ2aWV3IiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwic3RhZmYiLCJ1bWF' +
      'fYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sIm5hbWUiOiJTdW1lc2ggS2FyaXlpbCIsInByZWZlcnJlZF91c2VybmFtZSI6InNrYXJpeWlsQGlk' +
      'aXIiLCJlbWFpbCI6InN1bWVzaC5wLmthcml5aWxAZ292LmJjLmNhIiwibGFzdG5hbWUiOiJLYXJpeWlsIiwidXNlcm5hbWUiOiJza2FyaXlpb' +
      'EBpZGlyIn0.MSPSakOnCUia4qd-fUpvP2PB3k977Eyhjxn-ykjadsUTEK4f2R3c8vozxaIIMH0-qUwduyQmdZCl3tQnXYQ9Ttf1PE9eMLS4sX' +
      'JiIUlDmKZ2ow7GmmDabic8igHnEDYD6sI7OFYnCJhRdgVEHN-_4KUk2YsAVl5XUr6blJKMuYDPeMyNreGTXU7foE4AT-93FwlyTyFzQGddrDv' +
      'c6kkQr7mgJNTtgg87DdYbVGbEtIetyVfvwEF0rU8JH2N-j36XIebo33FU3-gJ5Y5S69EHPqQ37R9H4d8WUrHO-4QzJQih3Yaea820XBplJeo0' +
      'DO3hQoVtPD42j0p3aIy10cnW2g')
    // set business identified and user full name
    sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001867')
    sessionStorage.setItem('USER_FULL_NAME', 'First Last')

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
    wrapper = shallowMount(App, {
      localVue,
      router,
      store,
      vuetify })
    vm = wrapper.vm

    vm.$nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
    sessionStorage.clear()
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

    // These values have been assigned in the mockResponse but are expected to be filtered out by front-end logic.
    expect(vm.$store.state.registeredAddress.addressType).toBeUndefined()
  })

  it('fetches Directors properly', () => {
    expect(vm.$store.state.directors.length).toBe(2)
    expect(vm.$store.state.directors[0].officer.lastName).toBe('Griffin')
    expect(vm.$store.state.directors[1].officer.lastName).toBe('Swanson')
  })
})

describe('BCOMP APP', () => {
  // just need a token that can get parsed properly (will be expired but doesn't matter for tests)
  // must not include keycloakRoles=["staff"]
  let wrapper
  let vm

  beforeEach(done => {
    sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3F' +
      'QbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI0MmMzOWQzYi1iMTZkLTRiYWMtOWU1Ny1hNDYyZjQ3NWY0M2UiLCJleHAiO' +
      'jE1NzUwNzI4MTEsIm5iZiI6MCwiaWF0IjoxNTc1MDQ0MDExLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV' +
      '0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiI4ZTVkZDYzNS01OGRkLTQ5YzUtYmViM' +
      'S00NmE1ZDVhMTYzNWMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI' +
      '5OGQ3Y2Y2Zi0xYTQ1LTQzMzUtYWU0OC02YzBiNTdlMGYwNTAiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4L' +
      'jAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI' +
      '6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3Vud' +
      'CI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJ' +
      'yb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6I' +
      'mJjMDAwNzI5MSIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImJjMDAwNzI5MSJ9.GYKmp5SQxZYTEkltSgaM3LMNcmuo_n' +
      'b88wrYb6LbRk1BtCC0wU6Uu5zij_6mwXKyJ3dQ0L2EWR0eEqDuKzjWKVkIvQujXKzc8H9PPYPhgRqwdDr2qOglJrT2lJTkGZvPPqI217J2iiVW' +
      'OutPePeAmozIQhmf5jlZBW_J8qSzx9GmkQvT41hxpNLkaMPjPYVM2Iy6vL4Pnu0Xma-wCN1GCPwvJGQXCuh3IsR_iTMoig8qcFS0a0lUTx_cCj' +
      'G-zf_goG4vDTeKn6Mk50FToRtYGXkzWdfQn1T_yeS_2zrL8Ifg1QhJe74U_w40v4ikAFl-BofYnIRjopP57H-5g9_SGg')
    sessionStorage.setItem('BUSINESS_IDENTIFIER', 'BC0007291')
    const get = sinon.stub(axios, 'get')

    // GET authorizations (role)
    get.withArgs('BC0007291/authorizations')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            roles: ['edit', 'view']
          }
      })))

    // GET entity info
    // NB: contains responses for 2 axios calls with the same signature
    get.withArgs('BC0007291')
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
              identifier: 'BC0007291',
              lastLedgerTimestamp: '2019-08-14T22:27:12+00:00',
              foundingDate: '2000-07-13T00:00:00+00:00',
              lastAnnualGeneralMeetingDate: '2019-08-16',
              legalType: null
            }
          }
      })))

    // GET tasks
    get.withArgs('BC0007291/tasks')
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
    get.withArgs('BC0007291/filings')
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
    get.withArgs('BC0007291/addresses')
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
    get.withArgs('BC0007291/directors')
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
                },
                'mailingAddress': {
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
                },
                'mailingAddress': {
                  'streetAddress': '1012 Douglas St',
                  'addressCity': 'Victoria',
                  'addressRegion': 'BC',
                  'postalCode': 'V8W 2C3',
                  'addressCountry': 'CA'
                }
              }
            ]
          }
      })))

    // create a Local Vue and install router (and store) on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = new VueRouter()
    wrapper = shallowMount(App, {
      localVue,
      router,
      store,
      vuetify,
      destroyed () {
        get()
      } })
    vm = wrapper.vm

    vm.$nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
    sessionStorage.clear()
  })

  it('gets Keycloak Roles and Auth Roles properly', () => {
    expect(vm.$store.getters.isRoleStaff).toBe(false)
    expect(vm.$store.getters.isRoleEdit).toBe(true)
    expect(vm.$store.getters.isRoleView).toBe(true)

    sinon.restore()
    wrapper.destroy()
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
    expect(vm.$store.state.entityIncNo).toBe('BC0007291')
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
