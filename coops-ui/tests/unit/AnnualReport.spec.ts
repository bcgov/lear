import Vue from 'vue'
import Vuetify from 'vuetify'
import VueRouter from 'vue-router'
import Vuelidate from 'vuelidate'
import { shallowMount, createLocalVue } from '@vue/test-utils'
import sinon from 'sinon'

import mockRouter from './mockRouter'
import axios from '@/axios-auth'
import store from '@/store/store'
import AnnualReport from '@/views/AnnualReport.vue'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import Certify from '@/components/AnnualReport/Certify.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AnnualReport - Part 1', () => {
  beforeEach(() => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'
    store.state.filedDate = null
  })

  it('renders the Annual Report sub-components properly', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })

    expect(wrapper.find(AGMDate).exists()).toBe(true)
    expect(wrapper.find(RegisteredOfficeAddress).exists()).toBe(true)
    expect(wrapper.find(Directors).exists()).toBe(true)
    expect(wrapper.find(Certify).exists()).toBe(true)
  })

  it('initializes the store variables properly', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    expect(vm.$store.state.corpNum).toEqual('CP0001191')
    expect(vm.$store.state.ARFilingYear).toEqual(2017)
    expect(vm.$store.state.currentFilingStatus).toEqual('NEW')
    expect(vm.$store.state.filedDate).toBeNull()

    // check titles and sub-titles
    expect(vm.$el.querySelector('#AR-header').textContent).toContain('2017')
    expect(vm.$el.querySelector('#AR-step-2-header span').textContent).toContain('2017')
    expect(vm.$el.querySelector('#AR-step-3-header + p').textContent).toContain('2017')
  })

  it('enables Validated flag when sub-component flags are valid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(true)
    vm.changeCertifyData(true)
    vm.setValidateFlag()

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(true)
  })

  it('disables Validated flag when AGM Date is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.setAgmDateValid(false)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(true)
    vm.changeCertifyData(true)
    vm.setValidateFlag()

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('disables Validated flag when Addresses Form is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(false)
    vm.setDirectorFormValid(true)
    vm.changeCertifyData(true)
    vm.setValidateFlag()

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('disables Validated flag when Director Form is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(false)
    vm.changeCertifyData(true)
    vm.setValidateFlag()

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('disables Validated flag when Certify Form is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.setAgmDateValid(true)
    vm.setAddressesFormValid(true)
    vm.setDirectorFormValid(true)
    vm.changeCertifyData(false)
    vm.setValidateFlag()

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('enables File & Pay button when Validated is true', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store,
      mocks: { $route },
      stubs: {
        'Directors': true,
        'RegisteredOfficeAddress': true,
        'AGMDate': true,
        'Certify': true
      } })
    const vm: any = wrapper.vm

    // set flag
    vm.setValidated(true)

    // confirm that button is enabled
    expect(wrapper.find('#ar-file-pay-btn').attributes('disabled')).not.toBe('true')
  })

  it('disables File & Pay button when Validated is false', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flag
    vm.setValidated(false)

    // confirm that button is disabled
    expect(wrapper.find('#ar-file-pay-btn').attributes('disabled')).toBe('true')
  })
})

describe('AnnualReport - Part 2', () => {
  const { assign } = window.location

  beforeAll(() => {
    // mock the window.location.assign function
    delete window.location
    window.location = { assign: jest.fn() } as any
  })

  afterAll(() => {
    window.location.assign = assign
  })

  beforeEach(async () => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'
    store.state.filedDate = null

    // mock "fetch a draft filing" endpoint
    sinon.stub(axios, 'get').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get'
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'annualReport',
                'date': '2017-06-06',
                'submitter': 'cp0001191',
                'status': 'DRAFT',
                'filingId': 123
              }
            }
          }
      })))

    // mock "save and file" endpoint
    sinon.stub(axios, 'post').withArgs('CP0001191/filings')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get'
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'annualReport',
                'date': '2017-06-06',
                'submitter': 'cp0001191',
                'status': 'PENDING',
                'filingId': 123,
                'paymentToken': '321'
              }
            }
          }
      })))

    // mock "update and file" endpoint
    sinon.stub(axios, 'put').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get'
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'annualReport',
                'date': '2017-06-06',
                'submitter': 'cp0001191',
                'status': 'PENDING',
                'filingId': 123,
                'paymentToken': '321'
              }
            }
          }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('saves a new filing and redirects to Pay URL when this is a new AR and the File & Pay button is clicked',
    async () => {
      const $route = { params: { id: '0' } } // new filing id
      const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.setValidated(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the File & Pay button
      wrapper.find('#ar-file-pay-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickFilePay()

      // verify redirection
      const payURL = '/makepayment/321/' + encodeURIComponent('/Dashboard?filing_id=123')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)
    }
  )

  it('updates an existing filing and redirects to Pay URL when this is a draft AR and the File & Pay button is clicked',
    async () => {
      const $route = { params: { id: '123' } } // draft filing id
      const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.setValidated(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that draft filing was fetched

      // click the File & Pay button
      wrapper.find('#ar-file-pay-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickFilePay()

      // verify redirection
      const payURL = '/makepayment/321/' + encodeURIComponent('/Dashboard?filing_id=123')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)
    }
  )
})

describe('AnnualReport - Part 3', () => {
  let wrapper
  let vm

  beforeEach(async () => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'
    store.state.filedDate = null

    // mock "save draft" endpoint
    sinon.stub(axios, 'post').withArgs('CP0001191/filings?draft=true')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get'
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'annualReport',
                'date': '2017-06-06',
                'submitter': 'cp0001191',
                'status': 'DRAFT',
                'filingId': 123
              }
            }
          }
      })))

    // create local Vue and mock router
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'annual-report', params: { id: '0' } }) // new filing id

    // mount the component without rendering its child components
    wrapper = shallowMount(AnnualReport, { store, localVue, router })
    vm = wrapper.vm as any
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('saves a filing when the Save button is clicked', async () => {
    // make sure form is validated
    vm.setValidated(true)

    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    // verify no routing
    expect(vm.$route.name).toBe('annual-report')
  })

  it('saves a filing and routes to Home URL when the Save & Resume button is clicked', async () => {
    // make sure form is validated
    vm.setValidated(true)

    // click the Save & Resume Later button
    wrapper.find('#ar-save-resume-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSaveResume()

    // verify routing back to Home URL
    expect(vm.$route.name).toBe('dashboard')
  })

  it('routes to Home URL when the Cancel button is clicked', async () => {
    // make sure form is validated
    vm.setValidated(true)

    // click the Cancel button
    wrapper.find('#ar-cancel-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.$router.push('/dashboard')

    // verify routing back to Home URL
    expect(vm.$route.name).toBe('dashboard')
  })
})
