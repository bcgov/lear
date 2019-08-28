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
  // note - the corp num in this token is CP0001191
  sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N' +
    '3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIxYzQ2YjIzOS02ZWY0LTQxYTQtYThmMy05N2M5M2IyNmNlMjAiLCJle' +
    'HAiOjE1NTcxNzMyNTYsIm5iZiI6MCwiaWF0IjoxNTU3MTY5NjU2LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2' +
    'EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJzYmMtYXV0aC13ZWIiLCJzdWIiOiIwMzZlN2I4Ny0zZTQxLTQ2MTMtYjFiYy04NWU5OTA' +
    'xNTgzNzAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJkOGZmYjk4' +
    'OS0zNzRlLTRhYTktODc4OS03YTRkODA1ZjNkOTAiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6O' +
    'DA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl' +
    '0IiwidW1hX2F1dGhvcml6YXRpb24iLCJiYXNpYyJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY' +
    '291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTE5MSJ9.Ou' +
    'JLtzYCnkp5KXSiudGFJY6hTSvdE3KokhkEzqU-icxAzQwZSTYbzZQdGsIScy4-DIWHahIGp9L-e6mYlQSQta2rK2Kte85MxThubyw0096UOtAE' +
    'wnS9VURHXPUm4ZUyI4ECkyLlFywOPxAftNdeSYeJx26GHBCvo6uR9Zv6A3yTlJy3B1HJxBWk_6xTAzGPPDCLoyKGeIxGidGujKCKCAfXRMrjhX' +
    'yBv90XzDgZ-To-6_jMjSjBX6Dtq7icdZYLWWDdrhjCpJA5CKS0PlSgeH1Yq4rHd8Ztp5cvVdJFxt87gIopIOQvcy4ji0gtaovgUhiyg07gXGl8' +
    'dGZwn1tpLA')

  let wrapper
  let vm

  beforeEach(done => {
    const get = sinon.stub(axios, 'get')

    // GET entity info
    get.withArgs('CP0001191')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            business: {
              legalName: 'TEST NAME',
              status: 'GOODSTANDING',
              taxId: '123456789',
              identifier: 'CP0001191',
              lastLedgerTimestamp: '2019-08-14T22:27:12+00:00',
              foundingDate: '2000-07-13T00:00:00+00:00',
              lastAnnualGeneralMeetingDate: '2019-08-16'
            }
          }
      })))

    // GET tasks
    get.withArgs('CP0001191/tasks')
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
    get.withArgs('CP0001191/filings')
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
    get.withArgs('CP0001191/addresses')
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
    get.withArgs('CP0001191/directors')
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

  it('decodes Corp Num properly', () => {
    expect(vm.$store.state.corpNum).toEqual('CP0001191')
  })

  it('initializes Current Date properly', () => {
    const today = new Date()
    const year = today.getFullYear().toString()
    const month = (today.getMonth() + 1).toString().padStart(2, '0')
    const date = today.getDate().toString().padStart(2, '0')
    const currentDate = `${year}-${month}-${date}`
    expect(vm.$store.state.currentDate).toEqual(currentDate)
  })

  it('fetches the entity info properly', () => {
    expect(vm.$store.state.entityName).toBe('TEST NAME')
    expect(vm.$store.state.entityStatus).toBe('GOODSTANDING')
    expect(vm.$store.state.entityBusinessNo).toBe('123456789')
    expect(vm.$store.state.entityIncNo).toBe('CP0001191')
    expect(vm.$store.state.lastPreLoadFilingDate).toBe('2019-08-14')
    expect(vm.$store.state.entityFoundingDate).toBe('2000-07-13')
    expect(vm.$store.state.lastAgmDate).toBe('2019-08-16')
  })

  it('fetches the tasks properly', () => {
    expect(vm.$store.state.tasks.length).toBe(3)
    expect(vm.$store.state.tasks[0].task.todo.header.ARFilingYear).toBe(2017)
    expect(vm.$store.state.tasks[1].task.todo.header.ARFilingYear).toBe(2018)
    expect(vm.$store.state.tasks[2].task.todo.header.ARFilingYear).toBe(2019)
  })

  it('fetches the filings properly', () => {
    expect(vm.$store.state.filings.length).toBe(3)
    expect(vm.$store.state.filings[0].filing.header.name).toBe('annualReport')
    expect(vm.$store.state.filings[1].filing.header.name).toBe('changeOfDirectors')
    expect(vm.$store.state.filings[2].filing.header.name).toBe('changeOfAddress')
  })

  it('fetches the addresses properly', () => {
    expect(vm.$store.state.mailingAddress.addressCity).toBe('Victoria')
    expect(vm.$store.state.deliveryAddress.addressCity).toBe('Glasgow')
  })

  it('fetches the directors properly', () => {
    expect(vm.$store.state.directors.length).toBe(2)
    expect(vm.$store.state.directors[0].officer.lastName).toBe('Griffin')
    expect(vm.$store.state.directors[1].officer.lastName).toBe('Swanson')
  })
})
