import Vue from 'vue'
import Vuetify from 'vuetify'

import App from '@/App.vue'
import Home from '@/views/Home.vue'
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import store from '@/store'
import sinon from 'sinon'
import axios from '@/axios-auth.ts'
import Vuelidate from 'vuelidate'
Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('App.vue', () => {
  // just need a token that can get parsed properly (will be expired but doesn't matter for tests)
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
  let rootvm
  let vm
  let childvm

  let click = function (id) {
    console.log('ID: ', id)
    let button = vm.$el.querySelector(id)
    let window = button.ownerDocument.defaultView
    var click = new window.Event('click')
    button.dispatchEvent(click)
  }
  sinon.getStub = sinon.stub(axios, 'get')

  beforeEach((done) => {
    // reset store
    store.state.agmDate = null
    store.state.filedDate = null
    store.state.validated = false
    store.state.noAGM = false

    // ar info stub
    sinon.getStub.withArgs('CP0001191/filings/annual_report?year=2017')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            filing: {
              header: {
                name: 'annual report',
                date: '2016-04-08'
              },
              business_info: {
                founding_date: '2001-08-05',
                identifier: 'CP0001191',
                legal_name: 'legal name - CP0001191'
              },
              annual_report: {
                annual_general_meeting_date: '2016-04-08',
                certified_by: 'full name',
                email: 'no_one@never.get'
              }
            }
          }
      })))
    // business info stub
    sinon.getStub.withArgs('CP0001187')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            business_info: {
              founding_date: '2001-08-05',
              identifier: 'CP0001191',
              legal_name: 'legal name - CP0001191'
            }
          }
      })))
    // pay stub
    sinon.getStub.withArgs(
      'https://mock-lear-tools.pathfinder.gov.bc.ca/rest/pay/0.1/api/v1/payments/fees/AR/CP?date=2019-04-15')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            filingType: 'annual-report',
            corpType: 'CP',
            vaildDate: '2019-04-15',
            fees: {
              filing: 45,
              service: 1.5,
              processing: 0.75
            }
          }
      })))
    // pay-api-otann stub
    sinon.getStub.withArgs(
      'https://pay-api-dev.pathfinder.gov.bc.ca/api/v1/fees/CP/OTANN')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            filing_fees: 30,
            filing_type: 'ANNUAL REPORT',
            processing_fees: 0,
            service_fees: 0,
            tax: { gst: 0, pst: 0 },
            total: 30
          }
      })))

    const RootConstructor = Vue.extend(App)
    let rootInstance = new RootConstructor({ store: store })
    rootvm = rootInstance.$mount()

    const Constructor = Vue.extend(Home)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()

    const ChildConstructor = Vue.extend(AGMDate)
    let childInstance = new ChildConstructor({ store: store })
    childvm = childInstance.$mount()

    setTimeout(() => {
      done()
    }, 500)
  })

  afterEach((done) => {
    sinon.restore()
    setTimeout(() => {
      done()
    }, 750)
  })

  it('initializes the store variables properly', () => {
    expect(vm.$store.state.corpNum).toEqual('CP0001191')
    expect(vm.$store.state.ARFilingYear).toEqual('2017')
    expect(vm.$store.state.currentDate).toBeDefined()
    expect(vm.$store.state.filedDate).toBeNull()
    expect(vm.$store.state.agmDate).toBeNull()
    expect(vm.$store.state.noAGM).toBeFalsy()
    expect(vm.$store.state.validated).toBeFalsy()
    console.log('Passed Test 1')
  })

  // pay button disable based on 'validate' (store var)
  it('pay button disables based on validation', () => {
    // starts disabled
    expect(vm.$el.querySelector('#ar-pay-btn').getAttribute('disabled')).toBeTruthy()
    // when validated is true it becomes enabled
    vm.$store.state.validated = true
    setTimeout(() => {
      expect(vm.$el.querySelector('#ar-pay-btn').getAttribute('disabled')).toBeFalsy()
      console.log('Passed Test 2')
    }, 10)
  })

  // select noAGM and pay
  it('sets the store vars properly on \'no agm\' submit', () => {
    click('#agm-checkbox')
    setTimeout(() => {
      expect(vm.$store.state.noAGM).toBeTruthy()
      expect(vm.$store.state.validated).toBeTruthy()
      expect(vm.$el.querySelector('#ar-pay-btn').getAttribute('disabled')).toBeFalsy()
      click('#ar-pay-btn')
      setTimeout(() => {
        expect(vm.$store.state.ARFilingYear).toEqual('2017')
        expect(vm.$store.state.filedDate).toEqual(vm.$store.state.currentDate)
        expect(vm.$store.state.agmDate).toBeNull()
        console.log('Passed Test 3')
      }, 70)
    }, 50)
  })

  // select date and pay
  it('sets the store vars properly on \'selected date\' submit', () => {
    // select valid date
    var validMMDD = vm.$store.state.currentDate.substring(4)
    var myValidDate = vm.$store.state.ARFilingYear + validMMDD
    childvm.$data.date = myValidDate

    setTimeout(() => {
      expect(vm.$store.state.validated).toBeTruthy()
      expect(vm.$el.querySelector('#ar-pay-btn').getAttribute('disabled')).toBeFalsy()
      click('#ar-pay-btn')
      setTimeout(() => {
        expect(vm.$store.state.ARFilingYear).toEqual('2017')
        expect(vm.$store.state.filedDate).toEqual(vm.$store.state.currentDate)
        expect(vm.$store.state.agmDate).toEqual(myValidDate)
        console.log('Passed Test 4')
      }, 50)
    }, 10)
  })

  // next button
  it('the next button works after payment', () => {
    click('#agm-checkbox')
    setTimeout(() => {
      expect(vm.$store.state.noAGM).toBeTruthy()
      expect(vm.$store.state.validated).toBeTruthy()
      expect(vm.$el.querySelector('#ar-pay-btn').getAttribute('disabled')).toBeFalsy()
      click('#ar-pay-btn')
      setTimeout(() => {
        expect(vm.$store.state.filedDate).toBeDefined()
        expect(vm.$el.querySelector('#ar-next-btn').getAttribute('disabled')).toBeFalsy()
        // test disable button
        var tempYear = vm.$store.state.ARFilingYear
        vm.$store.state.ARFilingYear = vm.$store.state.currentDate.substring(0, 4)
        setTimeout(() => {
          expect(vm.$el.querySelector('#ar-next-btn').getAttribute('disabled')).toBeTruthy()
          vm.$store.state.ARFilingYear = tempYear
          setTimeout(() => {
            expect(vm.$el.querySelector('#ar-next-btn').getAttribute('disabled')).toBeFalsy()
            sinon.restore()
            sinon.getStub.withArgs('CP0001191/filings/annual_report?year=2017')
              .returns(new Promise((resolve) => resolve({
                data:
                  {
                    filing: {
                      header: {
                        name: 'annual report',
                        date: '2017-04-08'
                      },
                      business_info: {
                        founding_date: '2001-08-05',
                        identifier: 'CP0001191',
                        legal_name: 'legal name - CP0001191'
                      },
                      annual_report: {
                        annual_general_meeting_date: '2017-04-08',
                        certified_by: 'full name',
                        email: 'no_one@never.get'
                      }
                    }
                  }
              })))
            click('#ar-next-btn')
            setTimeout(() => {
              expect(vm.$store.state.corpNum).toEqual('CP0001191')
              expect(vm.$store.state.ARFilingYear).toEqual('2018')
              expect(vm.$store.state.currentDate).toBeDefined()
              expect(vm.$store.state.filedDate).toBeNull()
              expect(vm.$store.state.agmDate).toBeNull()
              expect(vm.$store.state.noAGM).toBeFalsy()
              expect(vm.$store.state.validated).toBeFalsy()
              console.log('Passed Test 5')
            }, 600)
          }, 10)
        }, 10)
      }, 50)
    }, 50)
  })
})
