import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import AnnualReport from '@/views/AnnualReport.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AnnualReport.vue', () => {
  let vm

  function click (id) {
    const button = vm.$el.querySelector(id)
    const window = button.ownerDocument.defaultView
    const click = new window.Event('click')
    button.dispatchEvent(click)
  }

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentARStatus = 'NEW'
    store.state.filedDate = null

    //
    // TODO - should stub out sub-components and just focus on THIS component's functionality
    //      - see Dashboard for example
    //

    const Constructor = Vue.extend(AnnualReport)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  it('initializes the store variables properly', () => {
    expect(vm.$store.state.corpNum).toEqual('CP0001191')
    expect(vm.$store.state.ARFilingYear).toEqual(2017)
    expect(vm.$store.state.currentARStatus).toEqual('NEW')
    expect(vm.$store.state.filedDate).toBeNull()

    // check titles and sub-titles
    expect(vm.$el.querySelector('#AR-header').textContent).toContain('2017')
    expect(vm.$el.querySelector('#AR-step-2-header span').textContent).toContain('2017')
    expect(vm.$el.querySelector('#AR-step-3-header + p').textContent).toContain('2017')

    console.log('Passed Test 1')
  })

  it('enables Validated flag when sub-component flags are valid', done => {
    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(true)
    vm.changeCertifyData(true)
    vm.setValidateFlag()

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.validated).toEqual(true)
      console.log('Passed Test 2')
      done()
    })
  })

  it('disables Validated flag when AGM Date is invalid', done => {
    // set flags
    vm.setAgmDateValid(false)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(true)
    vm.setValidateFlag()

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.validated).toEqual(false)
      console.log('Passed Test 3')
      done()
    })
  })

  it('disables Validated flag when Addresses Form is invalid', done => {
    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(false)
    vm.setDirectorFormValid(true)
    vm.setValidateFlag()

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.validated).toEqual(false)
      console.log('Passed Test 4')
      done()
    })
  })

  it('disables Validated flag when Director Form is invalid', done => {
    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(false)
    vm.setValidateFlag()

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.validated).toEqual(false)
      console.log('Passed Test 5')
      done()
    })
  })

  it('enables Pay & File button when Validated is true', done => {
    // set flag
    vm.setValidated(true)

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#ar-pay-btn').disabled).toBe(false)
      console.log('Passed Test 6')
      done()
    })
  })

  it('disables Pay & File button when Validated is false', done => {
    // set flag
    vm.setValidated(false)

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#ar-pay-btn').disabled).toBe(true)
      console.log('Passed Test 7')
      done()
    })
  })

  // TODO - fix this when Next button is implemented
  // next button
  // it('verifies that the next button works after payment', () => {
  //   // set flag
  //   vm.setValidateFlag(true)

  //   Vue.nextTick(() => {
  //     expect(vm.$store.state.noAGM).toBe(true)
  //     expect(vm.$store.state.validated).toBe(true)
  //     expect(vm.$el.querySelector('#ar-pay-btn').disabled).toBe(false)
  //     click('#ar-pay-btn')

  //     Vue.nextTick(() => {
  //       expect(vm.$store.state.filedDate).toBeDefined()
  //       expect(vm.$el.querySelector('#ar-next-btn').disabled).toBe(false)
  //       // test disable button
  //       var tempYear = vm.$store.state.ARFilingYear
  //       vm.$store.state.ARFilingYear = +vm.$store.state.currentDate.substring(0, 4)

  //       Vue.nextTick(() => {
  //         expect(vm.$el.querySelector('#ar-next-btn').disabled).toBe(true)
  //         vm.$store.state.ARFilingYear = tempYear

  //         Vue.nextTick(() => {
  //           expect(vm.$el.querySelector('#ar-next-btn').disabled).toBe(false)
  //           sinon.restore()
  //           sinon.getStub.withArgs('CP0001191/filings/1')
  //             .returns(new Promise((resolve) => resolve({
  //               data:
  //                 {
  //                   filing: {
  //                     annualReport: {
  //                       annualGeneralMeetingDate: '2016-04-08',
  //                       certifiedBy: 'full name',
  //                       email: 'no_one@never.get',
  //                       status: 'PENDING'
  //                     },
  //                     business: {
  //                       foundingDate: '2001-08-05',
  //                       identifier: 'CP0001191',
  //                       legalName: 'legal name - CP0001191'
  //                     },
  //                     header: {
  //                       date: '2016-04-08',
  //                       filingId: 1,
  //                       name: 'annualReport',
  //                       paymentToken: 'token',
  //                       status: 'PENDING' }
  //                   }
  //                 }
  //             })))
  //           click('#ar-next-btn')

  //           Vue.nextTick(() => {
  //             expect(vm.$store.state.corpNum).toEqual('CP0001191')
  //             expect(vm.$store.state.ARFilingYear).toEqual(2018)
  //             expect(vm.$store.state.currentDate).toBeDefined()
  //             expect(vm.$store.state.filedDate).toBeNull()
  //             // AGM Date is now initialized to 'minDate'
  //             expect(vm.$store.state.agmDate).toEqual('2018-01-01')
  //             expect(vm.$store.state.noAGM).toBe(false)
  //             expect(vm.$store.state.validated).toBe(false)
  //             console.log('Passed Test 8')
  //           })
  //         })
  //       })
  //     })
  //   })
  // })
})
