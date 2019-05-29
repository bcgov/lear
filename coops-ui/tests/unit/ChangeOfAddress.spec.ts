import Vue from 'vue'
import Vuetify from 'vuetify'

import App from '@/App.vue'
import Home from '@/views/Home.vue'
import RegisteredOfficeAddress from '@/components/ARSteps/RegisteredOfficeAddress.vue'
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
    let button = childvm.$el.querySelector(id)
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
                certifiedBy: 'tester',
                email: 'tester@testing.com'
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
              identifier: 'CP0001187',
              legal_name: 'legal name - CP0001187'
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
    // pay-api-otadd stub
    sinon.getStub.withArgs(
      'https://pay-api-dev.pathfinder.gov.bc.ca/api/v1/fees/CP/OTADD')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            filing_fees: 20,
            filing_type: 'Change of Registered Office Address',
            processing_fees: 0,
            service_fees: 0,
            tax: { gst: 0, pst: 0 },
            total: 20
          }
      })))
    // registered office info stub todo:replace with actual url
    sinon.getStub.withArgs('CP0001191/filings/changeOfAddress')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            header: {},
            business_info: {},
            filing: {
              certifiedBy: 'tester',
              email: 'tester@testing.com',
              deliveryAddress: {
                streetAddress: '1234 Main Street',
                streetAddressAdditional: '',
                addressCity: 'Victoria',
                addressRegion: 'BC',
                addressCountry: 'Canada',
                postalCode: 'V9A 2G8',
                deliveryInstructions: ''
              },
              mailingAddress: {
                streetAddress: '1234 Main Street',
                streetAddressAdditional: '',
                addressCity: 'Victoria',
                addressRegion: 'BC',
                addressCountry: 'Canada',
                postalCode: 'V9A 2G8',
                deliveryInstructions: ''
              }
            }
          }
      })))

    const RootConstructor = Vue.extend(App)
    let rootInstance = new RootConstructor({ store: store })
    rootvm = rootInstance.$mount()

    const Constructor = Vue.extend(Home)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()

    const ChildConstructor = Vue.extend(RegisteredOfficeAddress)
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
    expect(vm.$store.state.DeliveryAddressStreet).toEqual('1234 Main Street')
    expect(vm.$store.state.DeliveryAddressStreetAdditional).toEqual('')
    expect(vm.$store.state.DeliveryAddressCity).toEqual('Victoria')
    expect(vm.$store.state.DeliveryAddressRegion).toEqual('BC')
    expect(vm.$store.state.DeliveryAddressPostalCode).toEqual('V9A 2G8')
    expect(vm.$store.state.DeliveryAddressCountry).toEqual('Canada')
    expect(vm.$store.state.DeliveryAddressInstructions).toEqual('')
    expect(vm.$store.state.MailingAddressStreet).toEqual('1234 Main Street')
    expect(vm.$store.state.MailingAddressStreetAdditional).toEqual('')
    expect(vm.$store.state.MailingAddressCity).toEqual('Victoria')
    expect(vm.$store.state.MailingAddressRegion).toEqual('BC')
    expect(vm.$store.state.MailingAddressPostalCode).toEqual('V9A 2G8')
    expect(vm.$store.state.MailingAddressCountry).toEqual('Canada')
    expect(vm.$store.state.MailingAddressInstructions).toEqual('')
    expect(vm.$store.state.validated).toBeFalsy()
    console.log('Passed Test 1')
  })

  it('change button disabled based on agm filled', () => {
    // starts disabled
    expect(vm.$el.querySelector('#reg-off-addr-change-btn').getAttribute('disabled')).toBeTruthy()
    vm.$store.state.noAGM = true
    setTimeout(() => {
      expect(vm.$el.querySelector('#reg-off-addr-change-btn').getAttribute('disabled')).toBeFalsy()
      vm.$store.state.noAGM = false
      vm.$store.state.agmDate = '2018-01-01'
      setTimeout(() => {
        expect(vm.$el.querySelector('#reg-off-addr-change-btn').getAttribute('disabled')).toBeFalsy()
        console.log('Passed Test 2')
      }, 10)
    }, 10)
  })

  it('displays the non-editable version of the registered office address', () => {
    expect(childvm.$data.showAddressForm).toBeFalsy()
    if (childvm.$el.querySelector('#delivery-address-display').style.length > 0) {
      expect(childvm.$el.querySelector('#delivery-address-display').getAttribute('style')).not.toContain('display: none;')
    }
    if (childvm.$el.querySelector('#mailing-address-display').style.length > 0) {
      expect(childvm.$el.querySelector('#mailing-address-display').getAttribute('style')).not.toContain('display: none;')
    }
    expect(childvm.$el.querySelector('#delivery-address-form').getAttribute('style')).toContain('display: none;')
    expect(childvm.$el.querySelector('#mailing-address-form').getAttribute('style')).toContain('display: none;')
    console.log('Passed Test 3')
  })

  // select date and pay
  it('allows you to edit the addresses after entering agm', () => {
    childvm.$data.DeliveryAddressStreet = vm.$store.state.DeliveryAddressStreet
    childvm.$data.DeliveryAddressStreetAdditional = vm.$store.state.DeliveryAddressStreetAdditional
    childvm.$data.DeliveryAddressCity = vm.$store.state.DeliveryAddressCity
    childvm.$data.DeliveryAddressRegion = vm.$store.state.DeliveryAddressRegion
    childvm.$data.DeliveryAddressPostalCode = vm.$store.state.DeliveryAddressPostalCode
    childvm.$data.DeliveryAddressCountry = vm.$store.state.DeliveryAddressCountry
    childvm.$data.DeliveryAddressInstructions = vm.$store.state.DeliveryAddressInstructions
    childvm.$data.MailingAddressStreet = vm.$store.state.MailingAddressStreet
    childvm.$data.MailingAddressStreetAdditional = vm.$store.state.MailingAddressStreetAdditional
    childvm.$data.MailingAddressCity = vm.$store.state.MailingAddressCity
    childvm.$data.MailingAddressRegion = vm.$store.state.MailingAddressRegion
    childvm.$data.MailingAddressPostalCode = vm.$store.state.MailingAddressPostalCode
    childvm.$data.MailingAddressCountry = vm.$store.state.MailingAddressCountry
    childvm.$data.MailingAddressInstructions = vm.$store.state.MailingAddressInstructions
    vm.$store.state.noAGM = true
    setTimeout(() => {
      expect(vm.$store.state.regOffAddrChange).toBeFalsy()
      expect(childvm.$data.showAddressForm).toBeFalsy()
      expect(childvm.$el.querySelector('#reg-off-addr-change-btn')).not.toBeNull()
      expect(childvm.$el.querySelector('#reg-off-addr-reset-btn')).toBeNull()
      click('#reg-off-addr-change-btn')
      setTimeout(() => {
        // editable address form shown
        expect(childvm.$data.showAddressForm).toBeTruthy()
        if (childvm.$el.querySelector('#delivery-address-form').style.length > 0) {
          expect(childvm.$el.querySelector('#delivery-address-form').getAttribute('style')).not.toContain('display: none;')
        }
        if (childvm.$el.querySelector('#mailing-address-form').style.length > 0) {
          expect(childvm.$el.querySelector('#mailing-address-form').getAttribute('style')).not.toContain('display: none;')
        }
        expect(childvm.$el.querySelector('#delivery-address-display').getAttribute('style')).toContain('display: none;')
        expect(childvm.$el.querySelector('#mailing-address-display').getAttribute('style')).toContain('display: none;')
        expect(childvm.$data.inheritDeliveryAddress).toBeTruthy()
        expect(childvm.$el.querySelector('#mailing-address-expanded').getAttribute('style')).toContain('display: none;')
        childvm.$data.inheritDeliveryAddress = false
        setTimeout(() => {
          if (vm.$el.querySelector('#mailing-address-expanded').style.length > 0) {
            expect(childvm.$el.querySelector('#mailing-address-expanded').getAttribute('style')).not.toContain('display: none;')
          }
          expect(childvm.$el.querySelector('#reg-off-update-addr-btn').disabled).toBeFalsy()
          expect(childvm.$el.querySelector('#reg-off-cancel-addr-btn').disabled).toBeFalsy()
          childvm.$data.DeliveryAddressStreet = null
          setTimeout(() => {
            expect(childvm.$el.querySelector('#reg-off-update-addr-btn').disabled).toBeTruthy()
            childvm.$data.DeliveryAddressStreet = '1234'
            click('#reg-off-update-addr-btn')
            setTimeout(() => {
              expect(childvm.$data.showAddressForm).toBeFalsy()
              if (childvm.$el.querySelector('#delivery-address-display').style.length > 0) {
                expect(childvm.$el.querySelector('#delivery-address-display').getAttribute('style')).not.toContain('display: none;')
              }
              if (childvm.$el.querySelector('#mailing-address-display').style.length > 0) {
                expect(childvm.$el.querySelector('#mailing-address-display').getAttribute('style')).not.toContain('display: none;')
              }
              expect(childvm.$el.querySelector('#delivery-address-form').getAttribute('style')).toContain('display: none;')
              expect(childvm.$el.querySelector('#mailing-address-form').getAttribute('style')).toContain('display: none;')
              expect(vm.$store.state.regOffAddrChange).toBeTruthy()
              expect(childvm.$data.DeliveryAddressStreet).toEqual('1234')
              expect(childvm.$data.MailingAddressStreet).toEqual('1234 Main Street')
              expect(childvm.$el.querySelector('#reg-off-addr-reset-btn')).not.toBeNull()
              click('#reg-off-addr-change-btn')
              setTimeout(() => {
                childvm.$data.DeliveryAddressStreet = '12345678'
                childvm.$data.MailingAddressStreet = '12345678'
                expect(childvm.$el.querySelector('#reg-off-cancel-addr-btn')).not.toBeNull()
                click('#reg-off-cancel-addr-btn')
                setTimeout(() => {
                  expect(childvm.$data.DeliveryAddressStreet).toEqual('1234')
                  expect(childvm.$data.MailingAddressStreet).toEqual('1234 Main Street')
                  expect(childvm.$el.querySelector('#reg-off-addr-reset-btn')).not.toBeNull()
                  click('#reg-off-addr-reset-btn')
                  setTimeout(() => {
                    expect(childvm.$data.DeliveryAddressStreet).toEqual('1234 Main Street')
                    expect(vm.$store.state.regOffAddrChange).toBeFalsy()
                    expect(childvm.$el.querySelector('#reg-off-addr-reset-btn')).toBeNull()
                    console.log('Passed Test 4')
                  }, 10)
                }, 10)
              }, 10)
            }, 200)
          }, 10)
        }, 10)
      }, 100)
    }, 10)
  })
})
