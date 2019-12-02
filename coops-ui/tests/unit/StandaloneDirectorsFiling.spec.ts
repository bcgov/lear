/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'
import { createLocalVue, shallowMount, mount } from '@vue/test-utils'
import CODDate from '@/components/StandaloneDirectorChange/CODDate.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'
import axios from '@/axios-auth'
import store from '@/store/store'
import StandaloneDirectorsFiling from '@/views/StandaloneDirectorsFiling.vue'
import VueRouter from 'vue-router'
import mockRouter from './mockRouter'
import { BAD_REQUEST } from 'http-status-codes'
import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)
// suppress update watchers warnings
// ref: https://github.com/vuejs/vue-test-utils/issues/532
Vue.config.silent = true

let vuetify = new Vuetify({})

const sampleDirectors = [
  {
    'actions': [],
    'officer': {
      'firstName': 'Peter',
      'middleInitial': null,
      'lastName': 'Griffin'
    },
    'deliveryAddress': {
      'streetAddress': 'Peter Griffin delivery street address',
      'streetAddressAdditional': null,
      'addressCity': 'deliv address city',
      'addressCountry': 'deliv country',
      'postalCode': 'H0H0H0',
      'addressRegion': 'BC',
      'deliveryInstructions': null
    },
    'title': null,
    'appointmentDate': '2015-10-11',
    'cessationDate': null
  },
  {
    'actions': ['ceased', 'nameChanged'],
    'officer': {
      'firstName': 'Joe',
      'middleInitial': 'P',
      'lastName': 'Swanson'
    },
    'deliveryAddress': {
      'streetAddress': 'Joe Swanson delivery street address',
      'streetAddressAdditional': 'Kirkintiloch',
      'addressCity': 'Glasgow',
      'addressCountry': 'UK',
      'postalCode': 'H0H 0H0',
      'addressRegion': 'Scotland',
      'deliveryInstructions': 'go to the back'
    },
    'title': 'Treasurer',
    'appointmentDate': '2015-10-11',
    'cessationDate': '2019-07-22'
  }
]

describe('Standalone Directors Filing - Part 1 - UI', () => {
  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.currentDate = '2019/07/15'
  })

  it('renders the filing sub-components properly', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })

    expect(wrapper.find(CODDate).exists()).toBe(true)
    expect(wrapper.find(Directors).exists()).toBe(true)
    expect(wrapper.find(Certify).exists()).toBe(true)
    expect(wrapper.find(StaffPayment).exists()).toBe(false) // normally not rendered

    wrapper.destroy()
  })

  it('renders the Staff Payment sub-component properly', () => {
    // init store
    store.state.keycloakRoles = ['staff']

    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })

    // component should be displayed when totalFee > 0
    wrapper.setData({ totalFee: 1 })
    expect(wrapper.find(StaffPayment).exists()).toBe(true)

    // component should not be displayed when totalFee <= 0
    wrapper.setData({ totalFee: 0 })
    expect(wrapper.find(StaffPayment).exists()).toBe(false)

    // reset store
    // NB: this is important for subsequent tests
    store.state.keycloakRoles = []

    wrapper.destroy()
  })

  it('enables Validated flag when sub-component flags are valid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set properties
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(true)

    wrapper.destroy()
  })

  it('disables Validated flag when COD Date component is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set properties
    vm.codDateValid = false
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Directors component is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set properties
    vm.codDateValid = true
    vm.directorFormValid = false
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Certify component is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set properties
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = false
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Staff Payment data is required but not provided', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set properties
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummydata

    // set properties to make only staff payment invalid
    store.state.keycloakRoles = ['staff']
    vm.totalFee = 1
    vm.staffPaymentFormValid = false

    // confirm that form is invalid
    expect(vm.validated).toEqual(false)

    // toggle keycloak role to make payment valid
    store.state.keycloakRoles = []
    expect(vm.validated).toEqual(true)
    store.state.keycloakRoles = ['staff']

    // toggle total fee to make payment valid
    vm.totalFee = 0
    expect(vm.validated).toEqual(true)
    vm.totalFee = 1

    // toggle staff payment form valid to make payment valid
    vm.staffPaymentFormValid = true
    expect(vm.validated).toEqual(true)
    vm.staffPaymentFormValid = false

    // we should be back where we started
    expect(vm.validated).toEqual(false)

    // reset store
    // NB: this is important for subsequent tests
    store.state.keycloakRoles = []

    wrapper.destroy()
  })

  it('disables Validated flag when no filing changes were made (ie: nothing to file)', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set properties
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [] // no data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('enables File & Pay button when Validated is true', () => {
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id

    const wrapper = mount(StandaloneDirectorsFiling, {
      store,
      localVue,
      router,
      stubs: {
        CODDate: true,
        Directors: true,
        Certify: true,
        StaffPayment: true,
        Affix: true,
        SbcFeeSummary: true,
        ConfirmDialog: true,
        PaymentErrorDialog: true,
        ResumeErrorDialog: true,
        SaveErrorDialog: true
      },
      vuetify
    })
    const vm: any = wrapper.vm

    // set properties
    vm.inFilingReview = true
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that button is enabled
    expect(wrapper.find('#cod-file-pay-btn').attributes('disabled')).not.toBe('true')

    wrapper.destroy()
  })

  it('disables File & Pay button when Validated is false', () => {
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id

    const wrapper = mount(StandaloneDirectorsFiling, {
      store,
      localVue,
      router,
      stubs: {
        CODDate: true,
        Directors: true,
        Certify: true,
        StaffPayment: true,
        Affix: true,
        SbcFeeSummary: true,
        ConfirmDialog: true,
        PaymentErrorDialog: true,
        ResumeErrorDialog: true,
        SaveErrorDialog: true
      },
      vuetify
    })
    const vm: any = wrapper.vm

    // set properties
    vm.inFilingReview = true
    vm.codDateValid = false
    vm.directorFormValid = false
    vm.staffPaymentFormValid = false
    vm.certifyFormValid = false
    vm.filingData = [] // no data

    // confirm that button is disabled
    expect(wrapper.find('#cod-file-pay-btn').attributes('disabled')).toBe('disabled')

    wrapper.destroy()
  })
})

describe('Standalone Directors Filing - Part 2 - Resuming', () => {
  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'
    store.state.currentDate = '2019/07/15'

    // mock "fetch a draft filing" endpoint
    sinon.stub(axios, 'get').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': sampleDirectors
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfDirectors',
                'date': '2017-06-06T00:00:00+00:00',
                'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
                'submitter': 'cp0001191',
                'status': 'DRAFT',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
                'filingId': 123,
                'routingSlipNumber': '456'
              }
            }
          }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('fetches a draft Standalone Directors filing', done => {
    const $route = { params: { id: '123' } } // draft filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      // verify that Certified By was restored
      expect(vm.certifiedBy).toBe('Full Name')
      expect(vm.isCertified).toBe(false)

      // verify that Routing Slip Number was restored
      expect(vm.routingSlipNumber).toBe('456')

      // verify that we stored the Filing ID
      expect(+vm.filingId).toBe(123)

      // verify that we loaded the director data correctly
      expect(vm.filingData.filter(el => el.filingTypeCode === 'OTCDR').length).toEqual(1)
      expect(vm.filingData.filter(el => el.filingTypeCode === 'OTFDR').length).toEqual(1)

      wrapper.destroy()
      done()
    })
  })
})

describe('Standalone Directors Filing - Part 3A - Submitting filing that needs to be paid', () => {
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
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'

    // mock "fetch a draft filing" endpoint
    sinon.stub(axios, 'get').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': sampleDirectors
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfDirectors',
                'date': '2017-06-06T00:00:00+00:00',
                'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
                'submitter': 'cp0001191',
                'status': 'DRAFT',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
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
              'changeOfDirectors': {
                'directors': sampleDirectors
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfDirectors',
                'date': '2017-06-06T00:00:00+00:00',
                'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
                'submitter': 'cp0001191',
                'status': 'PENDING',
                'filingId': 123,
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
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
              'changeOfDirectors': {
                'directors': sampleDirectors
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfDirectors',
                'date': '2017-06-06T00:00:00+00:00',
                'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
                'submitter': 'cp0001191',
                'status': 'PENDING',
                'filingId': 123,
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
                'paymentToken': '321'
              }
            }
          }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('saves a new filing and redirects to Pay URL when this is a new filing and the File & Pay button ' +
    'is clicked - as a Coop', async () => {
    // init store
    store.state.entityType = EntityTypes.Coop

    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `myhost/${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', `myhost/${process.env.VUE_APP_AUTH_PATH}/`)

    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id
    const wrapper = mount(StandaloneDirectorsFiling, {
      store,
      localVue,
      router,
      stubs: {
        CODDate: true,
        Directors: true,
        Certify: true,
        StaffPayment: true,
        Affix: true,
        SbcFeeSummary: true,
        ConfirmDialog: true,
        PaymentErrorDialog: true,
        ResumeErrorDialog: true,
        SaveErrorDialog: true
      },
      vuetify
    })
    const vm: any = wrapper.vm as any

    // make sure form is validated
    vm.inFilingReview = true
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{ filingTypeCode: 'OTCDR', entityType: 'CP' }] // dummy data

    expect(vm.validated).toEqual(true)

    // make sure a fee is required
    vm.totalFee = 100

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // TODO: verify that new filing was created

    const button = wrapper.find('#cod-file-pay-btn')
    expect(button.attributes('disabled')).not.toBe('true')

    // click the File & Pay button
    button.trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    // verify v-tooltip text - Todo - Tool tip is outside the wrapper. Yet to find out how to get hold of that.
    // const tooltipText = wrapper.find('#cod-file-pay-btn + span').text()
    // expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
    // expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

    // verify redirection
    const payURL = 'myhost/cooperatives/auth/makepayment/321/' +
      encodeURIComponent('myhost/cooperatives/dashboard?filing_id=123')
    expect(window.location.assign).toHaveBeenCalledWith(payURL)

    wrapper.destroy()
  })

  it('saves a new filing and redirects to Pay URL when this is a new filing and the File & Pay button ' +
    'is clicked - as a Bcorp', async () => {
    // init store
    store.state.entityType = EntityTypes.BCorp

    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `myhost/${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', `myhost/${process.env.VUE_APP_AUTH_PATH}/`)

    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id
    const wrapper = mount(StandaloneDirectorsFiling, {
      store,
      localVue,
      router,
      stubs: {
        Directors: true,
        Certify: true,
        Affix: true,
        SbcFeeSummary: true,
        ConfirmDialog: true,
        PaymentErrorDialog: true,
        ResumeErrorDialog: true,
        SaveErrorDialog: true
      },
      vuetify
    })
    const vm: any = wrapper.vm as any

    // make sure form is validated
    vm.inFilingReview = true
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{ filingTypeCode: 'OTCDR', entityType: 'BC' }] // dummy data

    expect(vm.validated).toEqual(true)

    // make sure a fee is required
    vm.totalFee = 100

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // TODO: verify that new filing was created

    const button = wrapper.find('#cod-file-pay-btn')
    expect(button.attributes('disabled')).not.toBe('true')

    // click the File & Pay button
    button.trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    // verify v-tooltip text - Todo - Tool tip is outside the wrapper. Yet to find out how to get hold of that.
    // const tooltipText = wrapper.find('#cod-file-pay-btn + span').text()
    // expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
    // expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

    // verify redirection
    const payURL = 'myhost/cooperatives/auth/makepayment/321/' +
      encodeURIComponent('myhost/cooperatives/dashboard?filing_id=123')
    expect(window.location.assign).toHaveBeenCalledWith(payURL)

    wrapper.destroy()
  })

  it('updates an existing filing and redirects to Pay URL when this is a draft filing and the File & Pay button ' +
    'is clicked', async () => {
    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `myhost/${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', `myhost/${process.env.VUE_APP_AUTH_PATH}/`)

    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '123' } }) // existing filing id
    const wrapper = mount(StandaloneDirectorsFiling, {
      store,
      localVue,
      router,
      stubs: {
        CODDate: true,
        Directors: true,
        Certify: true,
        StaffPayment: true,
        Affix: true,
        SbcFeeSummary: true,
        ConfirmDialog: true,
        PaymentErrorDialog: true,
        ResumeErrorDialog: true,
        SaveErrorDialog: true
      },
      vuetify
    })
    const vm: any = wrapper.vm as any

    // make sure form is validated
    vm.inFilingReview = true
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data

    expect(vm.validated).toEqual(true)

    // make sure a fee is required
    vm.totalFee = 100

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // TODO: verify that draft filing was fetched

    const button = wrapper.find('#cod-file-pay-btn')
    expect(button.attributes('disabled')).not.toBe('true')

    // click the File & Pay button
    button.trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    // verify v-tooltip text - To find out how to get the tool tip text outside the wrapper
    // const tooltipText = wrapper.find('#cod-file-pay-btn + span').text()
    // expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
    // expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

    // verify redirection
    const payURL = 'myhost/cooperatives/auth/makepayment/321/' +
      encodeURIComponent('myhost/cooperatives/dashboard?filing_id=123')
    expect(window.location.assign).toHaveBeenCalledWith(payURL)

    wrapper.destroy()
  })
})

describe('Standalone Directors Filing - Part 3B - Submitting filing that doesn\'t need to be paid', () => {
  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'

    // mock "save and file" endpoint
    sinon.stub(axios, 'post').withArgs('CP0001191/filings')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': sampleDirectors
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfDirectors',
                'date': '2017-06-06T00:00:00+00:00',
                'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
                'submitter': 'cp0001191',
                'status': 'PAID', // API may return this or PENDING but we don't care
                'filingId': 123,
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
                'paymentToken': '321'
              }
            }
          }
      })))

    sinon.stub(axios, 'get').withArgs('CP0001191/tasks')
      .returns(new Promise((resolve) => resolve({
        data: {
          'tasks': [
            {
              'task': {
                'filing': {
                  'header': {
                    'name': 'annualReport',
                    'ARFilingYear': 2017,
                    'status': 'NEW'
                  }
                }
              },
              'enabled': true,
              'order': 1
            }
          ]
        }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('saves a new filing and routes to Dashboard URL when this is a new filing and the File & Pay button ' +
    'is clicked', async () => {
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id

    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, localVue, router })
    const vm: any = wrapper.vm as any

    // make sure form is validated
    vm.inFilingReview = true
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{ filingTypeCode: 'OTFDR', entityType: 'CP' }] // dummy data

    // go to summary page
    vm.showSummary()

    wrapper.find('#cod-file-pay-btn')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    // verify routing back to Dashboard URL
    expect(vm.$route.name).toBe('dashboard')

    // verify route param
    expect(vm.$route.query).toEqual({ filing_id: '123' })

    wrapper.destroy()
  })
})

describe('Standalone Directors Filing - Part 4 - Saving', () => {
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
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'

    // mock "save draft" endpoint
    sinon.stub(axios, 'post').withArgs('CP0001191/filings?draft=true')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': sampleDirectors
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfDirectors',
                'date': '2017-06-06T00:00:00+00:00',
                'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
                'submitter': 'cp0001191',
                'status': 'DRAFT',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
                'filingId': 123
              }
            }
          }
      })))

    sinon.stub(axios, 'get').withArgs('CP0001191/tasks')
      .returns(new Promise((resolve) => resolve({
        data: {
          'tasks': [
            {
              'task': {
                'filing': {
                  'header': {
                    'name': 'annualReport',
                    'ARFilingYear': 2017,
                    'status': 'NEW'
                  }
                }
              },
              'enabled': true,
              'order': 1
            }
          ]
        }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('saves a new filing when this is a new filing and the Save button is clicked',
    async () => {
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.codDateValid = true
      vm.directorFormValid = true
      vm.staffPaymentFormValid = true
      vm.certifyFormValid = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the Save button
      wrapper.find('#cod-save-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickSave()

      // verify no redirection
      expect(window.location.assign).not.toHaveBeenCalled()

      wrapper.destroy()
    }
  )

  it('saves a new filing and routes to Dashboard URL when the Save & Resume button is clicked', async () => {
    // create local Vue and mock router
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id

    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, localVue, router })
    const vm = wrapper.vm as any

    // make sure form is validated
    vm.inFilingReview = true
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true

    // click the Save & Resume Later button
    wrapper.find('#cod-save-resume-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSaveResume()

    // verify routing back to Dashboard URL
    expect(vm.$route.name).toBe('dashboard')

    wrapper.destroy()
  })
})

describe('Standalone Directors Filing - Part 5 - Data', () => {
  let wrapper
  let vm
  let spy

  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'

    // mock "save draft" endpoint - garbage response data, we aren't testing that
    spy = sinon.stub(axios, 'post').withArgs('CP0001191/filings?draft=true')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': []
              },
              'business': {
              },
              'header': {
                'filingId': 123
              }
            }
          }
      })))

    // create local Vue and mock router
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id

    wrapper = shallowMount(StandaloneDirectorsFiling, { store, localVue, router })
    vm = wrapper.vm as any

    // set up director data
    vm.allDirectors = [
      // unchanged director
      {
        officer: {
          firstName: 'Unchanged',
          lastName: 'lastname'
        },
        deliveryAddress: {
          streetAddress: 'a1',
          addressCity: 'city',
          addressCountry: 'country',
          postalCode: 'H0H0H0',
          addressRegion: 'BC'
        },
        appointmentDate: '2019-01-01',
        cessationDate: null,
        actions: []
      },
      // appointed director
      {
        officer: {
          firstName: 'Appointed',
          lastName: 'lastname'
        },
        deliveryAddress: {
          streetAddress: 'a1',
          addressCity: 'city',
          addressCountry: 'country',
          postalCode: 'H0H0H0',
          addressRegion: 'BC'
        },
        appointmentDate: '2019-01-01',
        cessationDate: null,
        actions: ['appointed']
      },
      // ceased director
      {
        officer: {
          firstName: 'Ceased',
          lastName: 'lastname'
        },
        deliveryAddress: {
          streetAddress: 'a1',
          addressCity: 'city',
          addressCountry: 'country',
          postalCode: 'H0H0H0',
          addressRegion: 'BC'
        },
        appointmentDate: '2019-01-01',
        cessationDate: '2019-03-25',
        actions: ['ceased']
      }
    ]

    // make sure form is validated
    vm.codDateValid = true
    vm.directorFormValid = true
    vm.staffPaymentFormValid = true
    vm.certifyFormValid = true

    vm.directorsChange(true)
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('Includes complete list of directors in the filing data', async () => {
    // click the Save button
    wrapper.find('#cod-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.changeOfDirectors).toBeDefined()

    let names = payload.filing.changeOfDirectors.directors.map(el => el.officer.firstName)
    expect(names).toContain('Unchanged')
    expect(names).toContain('Appointed')
    expect(names).toContain('Ceased')
  })

  it('Includes certification data in the header', async () => {
    // click the Save button
    wrapper.find('#cod-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.changeOfDirectors).toBeDefined()
    expect(payload.filing.header).toBeDefined()

    expect(payload.filing.header.certifiedBy).toBeDefined()
    expect(payload.filing.header.email).toBeDefined()
  })
})

describe('Standalone Directors Filing - Part 6 - Error/Warning dialogues', () => {
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
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'

    // mock "file post" endpoint
    const p1 = Promise.reject({
      response: {
        status: BAD_REQUEST,
        data: {
          'errors': [
            {
              'error': 'err msg post',
              'path': 'swkmc/sckmr'
            }
          ],
          'warnings': [
            {
              'warning': 'warn msg post',
              'path': 'swkmc/sckmr'
            }
          ],
          'filing': {
            'changeOfDirectors': {
              'directors': sampleDirectors
            },
            'business': {
              'cacheId': 1,
              'foundingDate': '2007-04-08T00:00:00+00:00',
              'identifier': 'CP0001191',
              'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
              'legalName': 'Legal Name - CP0001191'
            },
            'header': {
              'name': 'changeOfDirectors',
              'date': '2017-06-06T00:00:00+00:00',
              'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
              'submitter': 'cp0001191',
              'status': 'PENDING',
              'filingId': 123,
              'certifiedBy': 'Full Name',
              'email': 'no_one@never.get',
              'paymentToken': '321'
            }
          }
        }
      }
    })
    p1.catch(() => {}) // pre-empt "unhandled promise rejection" warning
    sinon.stub(axios, 'post').withArgs('CP0001191/filings').returns(p1)

    // mock "file put" endpoint
    const p2 = Promise.reject({
      response: {
        status: BAD_REQUEST,
        data: {
          'errors': [
            {
              'error': 'err msg put',
              'path': 'swkmc/sckmr'
            }
          ],
          'warnings': [
            {
              'warning': 'warn msg put',
              'path': 'swkmc/sckmr'
            }
          ],
          'filing': {
            'changeOfDirectors': {
              'directors': sampleDirectors
            },
            'business': {
              'cacheId': 1,
              'foundingDate': '2007-04-08T00:00:00+00:00',
              'identifier': 'CP0001191',
              'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
              'legalName': 'Legal Name - CP0001191'
            },
            'header': {
              'name': 'changeOfDirectors',
              'date': '2017-06-06T00:00:00+00:00',
              'effectiveDate': 'Tue, 06 Jun 2017 18:49:44 GMT',
              'submitter': 'cp0001191',
              'status': 'PENDING',
              'filingId': 123,
              'certifiedBy': 'Full Name',
              'email': 'no_one@never.get',
              'paymentToken': '321'
            }
          }
        }
      }
    })
    p2.catch(() => {}) // pre-empt "unhandled promise rejection" warning
    sinon.stub(axios, 'put').withArgs('CP0001191/filings/123').returns(p2)
  })

  afterEach(() => {
    sinon.restore()
  })

  it('sets the required fields to display errors from the api after a POST call',
    async () => {
      const localVue = createLocalVue()
      localVue.use(VueRouter)
      const router = mockRouter.mock()
      router.push({ name: 'standalone-directors', params: { id: '0' } }) // new filing id
      const wrapper = mount(StandaloneDirectorsFiling, {
        store,
        localVue,
        router,
        stubs: {
          CODDate: true,
          Directors: true,
          Certify: true,
          StaffPayment: true,
          Affix: true,
          SbcFeeSummary: true,
          ConfirmDialog: true,
          PaymentErrorDialog: true,
          ResumeErrorDialog: true,
          SaveErrorDialog: true
        },
        vuetify
      })
      const vm: any = wrapper.vm as any

      // make sure form is validated
      vm.inFilingReview = true
      vm.codDateValid = true
      vm.directorFormValid = true
      vm.staffPaymentFormValid = true
      vm.certifyFormValid = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that draft filing was fetched

      // click the File & Pay button
      wrapper.find('#cod-file-pay-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickFilePay()

      // verify error dialogue values set to what was returned
      expect(vm.saveErrorDialog).toBe(true)
      expect(vm.saveErrors.length).toBe(1)
      expect(vm.saveErrors[0].error).toBe('err msg post')
      expect(vm.saveWarnings.length).toBe(1)
      expect(vm.saveWarnings[0].warning).toBe('warn msg post')

      wrapper.destroy()
    }
  )

  it('sets the required fields to display errors from the api after a PUT call',
    async () => {
      const localVue = createLocalVue()
      localVue.use(VueRouter)
      const router = mockRouter.mock()
      router.push({ name: 'standalone-directors', params: { id: '123' } }) // existing filing id
      const wrapper = mount(StandaloneDirectorsFiling, {
        store,
        localVue,
        router,
        stubs: {
          CODDate: true,
          Directors: true,
          Certify: true,
          StaffPayment: true,
          Affix: true,
          SbcFeeSummary: true,
          ConfirmDialog: true,
          PaymentErrorDialog: true,
          ResumeErrorDialog: true,
          SaveErrorDialog: true
        },
        vuetify
      })
      const vm: any = wrapper.vm as any

      // make sure form is validated
      vm.inFilingReview = true
      vm.codDateValid = true
      vm.directorFormValid = true
      vm.staffPaymentFormValid = true
      vm.certifyFormValid = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that draft filing was fetched

      // click the File & Pay button
      wrapper.find('#cod-file-pay-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickFilePay()

      // verify error dialogue values set to what was returned
      expect(vm.saveErrorDialog).toBe(true)
      expect(vm.saveErrors.length).toBe(1)
      expect(vm.saveErrors[0].error).toBe('err msg put')
      expect(vm.saveWarnings.length).toBe(1)
      expect(vm.saveWarnings[0].warning).toBe('warn msg put')

      wrapper.destroy()
    }
  )
})
