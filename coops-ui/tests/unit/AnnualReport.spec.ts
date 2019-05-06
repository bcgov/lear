import Vue from 'vue'
import Vuetify from 'vuetify'

import Home from '@/views/Home.vue'
import AGMDate from '@/components/ARSteps/AGMDate.vue'
import store from '@/store'
import sinon from 'sinon'
import axios from '@/axios-auth.ts'
Vue.use(Vuetify)

describe('Home.vue', () => {
  sessionStorage.setItem('KEYCLOAK_TOKEN', '1234abcd')
  sessionStorage.setItem('USERNAME', 'CP0001191')
  const Constructor = Vue.extend(Home)
  let instance = new Constructor({ store: store })
  let vm = instance.$mount()

  const ChildConstructor = Vue.extend(AGMDate)
  let childInstance = new ChildConstructor({ store: store })
  let childvm = childInstance.$mount()

  let click = function (id) {
    console.log('ID: ', id)
    let button = vm.$el.querySelector(id)
    let window = button.ownerDocument.defaultView
    var click = new window.Event('click')
    button.dispatchEvent(click)
  }
  // ar info stub
  sinon.getStub = sinon.stub(axios, 'get')
  sinon.getStub.withArgs(
    'https://mock-lear-tools.pathfinder.gov.bc.ca/rest/legal-api/0.64/api/v1/businesses/' +
    'CP0001191/filings/annual_report?year=2017')
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

  beforeEach((done) => {
    // reset store
    vm.$store.state.agmDate = null
    vm.$store.state.filedDate = null
    vm.$store.state.validated = false
    vm.$store.state.noAGM = false
    setTimeout(() => {
      done()
    }, 100)
  })

  afterEach((done) => {
    setTimeout(() => {
      done()
    }, 200)
  })

  it('initializes the store variables properly', () => {
    expect(sessionStorage.getItem('KEYCLOAK_TOKEN')).toEqual('1234abcd')
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
            click('#ar-next-btn')
            setTimeout(() => {
              expect(vm.$store.state.corpNum).toEqual('CP0001191')
              expect(vm.$store.state.ARFilingYear).toEqual('2017')
              expect(vm.$store.state.currentDate).toBeDefined()
              expect(vm.$store.state.filedDate).toBeNull()
              expect(vm.$store.state.agmDate).toBeNull()
              expect(vm.$store.state.noAGM).toBeFalsy()
              expect(vm.$store.state.validated).toBeFalsy()
              console.log('Passed Test 5')
            }, 50)
          }, 10)
        }, 10)
      }, 50)
    }, 50)
  })
})
