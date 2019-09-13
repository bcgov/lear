/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import VueRouter from 'vue-router'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'
import { shallowMount, createLocalVue } from '@vue/test-utils'

import mockRouter from './mockRouter'
import axios from '@/axios-auth'
import store from '@/store/store'
import AnnualReport from '@/views/AnnualReport.vue'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import { BAD_REQUEST } from 'http-status-codes'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AnnualReport - Part 1 - UI', () => {
  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'
  })

  it('renders the Annual Report sub-components properly', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })

    expect(wrapper.find(AGMDate).exists()).toBe(true)
    expect(wrapper.find(RegisteredOfficeAddress).exists()).toBe(true)
    expect(wrapper.find(Directors).exists()).toBe(true)
    expect(wrapper.find(Certify).exists()).toBe(true)

    wrapper.destroy()
  })

  it('initializes the store variables properly', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    expect(vm.$store.state.entityIncNo).toEqual('CP0001191')
    expect(vm.$store.state.ARFilingYear).toEqual(2017)
    expect(vm.$store.state.currentFilingStatus).toEqual('NEW')

    // check titles and sub-titles
    expect(vm.$el.querySelector('#AR-header').textContent).toContain('2017')
    expect(vm.$el.querySelector('#AR-step-2-header span').textContent).toContain('2017')
    expect(vm.$el.querySelector('#AR-step-3-header + p').textContent).toContain('2017')

    wrapper.destroy()
  })

  it('enables Validated flag when sub-component flags are valid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(true)
    expect(vm.isSaveButtonEnabled).toEqual(true)

    wrapper.destroy()
  })

  it('disables Validated flag when AGM Date is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.agmDateValid = false
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(false)
    expect(vm.isSaveButtonEnabled).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Addresses Form is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.agmDateValid = true
    vm.addressesFormValid = false
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(false)
    expect(vm.isSaveButtonEnabled).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Director Form is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = false
    vm.certifyFormValid = true

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(false)
    expect(vm.isSaveButtonEnabled).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Certify Form is invalid', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = false

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(false)
    expect(vm.isSaveButtonEnabled).toEqual(true)

    wrapper.destroy()
  })

  it('enables File & Pay button when form is validated', () => {
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

    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // confirm that button is enabled
    expect(wrapper.find('#ar-file-pay-btn').attributes('disabled')).not.toBe('true')

    wrapper.destroy()
  })

  it('disables File & Pay button when form is not validated', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.agmDateValid = false
    vm.addressesFormValid = false
    vm.directorFormValid = false
    vm.certifyFormValid = false

    // confirm that button is disabled
    expect(wrapper.find('#ar-file-pay-btn').attributes('disabled')).toBe('true')

    wrapper.destroy()
  })
})

describe('AnnualReport - Part 2 - Resuming', () => {
  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'DRAFT'

    // mock "fetch a draft filing" endpoint
    sinon.stub(axios, 'get').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15'
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
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
                'filingId': 123
              }
            }
          }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('fetches a draft AR filing', done => {
    const $route = { params: { id: '123' } } // draft filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      // FUTURE: verify that Draft Date (for directors) was restored
      // (should be '2018-07-15')

      // FUTURE: verify that AGM Date was restored
      // (should be '2018/07/15')

      // verify that Certified By was restored
      expect(vm.certifiedBy).toBe('Full Name')
      expect(vm.isCertified).toBe(false)

      // verify that we stored the Filing ID
      expect(+vm.filingId).toBe(123)

      // FUTURE: verify that changed addresses and directors were restored
      // (need to include in data above)

      wrapper.destroy()
      done()
    })
  })
})

describe('AnnualReport - Part 3 - Submitting', () => {
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
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'

    // mock "fetch a draft filing" endpoint
    sinon.stub(axios, 'get').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15'
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
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15'
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
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15'
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

  it('saves a new filing and redirects to Pay URL when this is a new AR and the File & Pay button is clicked',
    async () => {
      const $route = { params: { id: '0' } } // new filing id
      const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.agmDateValid = true
      vm.addressesFormValid = true
      vm.directorFormValid = true
      vm.certifyFormValid = true

      // stub address data
      vm.addresses = {
        'deliveryAddress': {},
        'mailingAddress': {}
      }

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      const button = wrapper.find('#ar-file-pay-btn')
      expect(button.attributes('disabled')).toBeUndefined()

      // click the File & Pay button
      button.trigger('click')
      // work-around because click trigger isn't working
      expect(await vm.onClickFilePay()).toBe(true)

      // verify v-tooltip text
      const tooltipText = wrapper.find('#ar-file-pay-btn + span').text()
      expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
      expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

      // verify redirection
      const payURL = '/makepayment/321/' + encodeURIComponent('/dashboard?filing_id=123')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
    }
  )

  it('updates an existing filing and redirects to Pay URL when this is a draft AR and the ' +
    'File & Pay button is clicked',
  async () => {
    const $route = { params: { id: '123' } } // draft filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    const button = wrapper.find('#ar-file-pay-btn')
    expect(button.attributes('disabled')).toBeUndefined()

    // click the File & Pay button
    button.trigger('click')
    // work-around because click trigger isn't working
    expect(await vm.onClickFilePay()).toBe(true)

    // verify v-tooltip text
    const tooltipText = wrapper.find('#ar-file-pay-btn + span').text()
    expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
    expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

    // verify redirection
    const payURL = '/makepayment/321/' + encodeURIComponent('/dashboard?filing_id=123')
    expect(window.location.assign).toHaveBeenCalledWith(payURL)

    wrapper.destroy()
  })

  it('disables File & Pay button if user has \'staff\' role', async () => {
    // init store
    store.state.keycloakRoles = ['staff']

    const $route = { params: { id: '123' } } // draft filing id
    const wrapper = shallowMount(AnnualReport, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // verify that onClickFilePay() does nothing
    expect(await vm.onClickFilePay()).toBe(false)

    // verify v-tooltip text
    expect(wrapper.find('#ar-file-pay-btn + span').text()).toBe('Staff are not allowed to file.')

    store.state.keycloakRoles = [] // cleanup

    wrapper.destroy()
  })
})

describe('AnnualReport - Part 4 - Saving', () => {
  let wrapper
  let vm

  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'

    // mock "save draft" endpoint
    sinon.stub(axios, 'post').withArgs('CP0001191/filings?draft=true')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
                'annualGeneralMeetingDate': '2018-07-15'
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
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
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

    wrapper = shallowMount(AnnualReport, { store, localVue, router })
    vm = wrapper.vm as any
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('saves a new filing when the Save button is clicked', async () => {
    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    // verify no routing
    expect(vm.$route.name).toBe('annual-report')
  })

  it('saves a filing and routes to Dashboard URL when the Save & Resume button is clicked', async () => {
    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // click the Save & Resume Later button
    wrapper.find('#ar-save-resume-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSaveResume()

    // verify routing back to Dashboard URL
    expect(vm.$route.name).toBe('dashboard')
  })

  it('routes to Dashboard URL when the Cancel button is clicked', async () => {
    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // click the Cancel button
    wrapper.find('#ar-cancel-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.$router.push('/dashboard')

    // verify routing back to Dashboard URL
    expect(vm.$route.name).toBe('dashboard')
  })
})

describe('AnnualReport - Part 5 - Data', () => {
  let wrapper
  let vm
  let spy

  const currentFilingYear = 2017

  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityName = 'Legal Name - CP0001191'
    store.state.ARFilingYear = currentFilingYear
    store.state.currentFilingStatus = 'NEW'

    // mock "save draft" endpoint - garbage response data, we aren't testing that
    spy = sinon.stub(axios, 'post').withArgs('CP0001191/filings?draft=true')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'annualReport': {
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
    router.push({ name: 'annual-report', params: { id: '0' } }) // new filing id

    wrapper = shallowMount(AnnualReport, { store, localVue, router })
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

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('Includes Directors, Office Mailing Address, and Office Delivery Address in AR filing data', async () => {
    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    // get the payload of the ajax call
    // - the first index (0) is to get the first call, where there could be many calls to the stubbed function
    // - the second index (1) is to get the second param - data - where the call is axios.post(url, data)
    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()

    expect(payload.filing.annualReport.directors).toBeDefined()
    expect(payload.filing.annualReport.mailingAddress).toBeDefined()
    expect(payload.filing.annualReport.deliveryAddress).toBeDefined()
  })

  it('Includes unchanged directors in AR filing data', async () => {
    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()
    expect(payload.filing.annualReport.directors).toBeDefined()

    let names = payload.filing.annualReport.directors.map(el => el.officer.firstName)
    expect(names).toContain('Unchanged')
  })

  it('Includes appointed directors in AR filing data', async () => {
    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()
    expect(payload.filing.annualReport.directors).toBeDefined()

    let names = payload.filing.annualReport.directors.map(el => el.officer.firstName)
    expect(names).toContain('Appointed')
  })

  it('Does NOT include ceased directors in AR filing data', async () => {
    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()
    expect(payload.filing.annualReport.directors).toBeDefined()

    let names = payload.filing.annualReport.directors.map(el => el.officer.firstName)
    expect(names).not.toContain('Ceased')
  })

  it('Includes certification data in the header', async () => {
    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()
    expect(payload.filing.header).toBeDefined()

    expect(payload.filing.header.certifiedBy).toBeDefined()
    expect(payload.filing.header.email).toBeDefined()
  })

  it('Includes the AR Date for the current filing year', async () => {
    // set current date in store, since it's normally set in a different component
    store.state.currentDate = '2019-03-03'

    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()
    expect(payload.filing.annualReport.annualReportDate).toBeDefined()

    expect(payload.filing.annualReport.annualReportDate.substr(0, 4)).toBe(currentFilingYear.toString())
  })

  it('Sets the AGM Date and AR Date correctly for "No AGM" filing', async () => {
    // set current date in store, since it's normally set in a different component
    store.state.currentDate = '2019-03-03'

    // set No AGM
    vm.noAGM = true
    vm.agmDate = null

    // click the Save button
    wrapper.find('#ar-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.annualReport).toBeDefined()
    expect(payload.filing.annualReport.annualReportDate).toBeDefined()

    // AGM Date should be null
    expect(payload.filing.annualReport.annualGeneralMeetingDate).toBeNull()

    // AR Date (year) should be filing year (ie: AR owed)
    expect(payload.filing.annualReport.annualReportDate.substr(0, 4)).toBe(currentFilingYear.toString())
  })
})

describe('AnnualReport - Part 6 - Error/Warning dialogues', () => {
  let wrapper
  let vm
  const request = require('request')
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
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'

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
            'annualReport': {
              'annualGeneralMeetingDate': '2018-07-15'
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
              'certifiedBy': 'Full Name',
              'email': 'no_one@never.get',
              'filingId': 123
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
            'annualReport': {
              'annualGeneralMeetingDate': '2018-07-15'
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
              'certifiedBy': 'Full Name',
              'email': 'no_one@never.get',
              'filingId': 123
            }
          }
        }
      }
    })
    p2.catch(() => {}) // pre-empt "unhandled promise rejection" warning
    sinon.stub(axios, 'put').withArgs('CP0001191/filings/123').returns(p2)

    // create local Vue and mock router
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'annual-report', params: { id: '0' } }) // new filing id

    wrapper = shallowMount(AnnualReport, { store, localVue, router })
    vm = wrapper.vm as any
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('sets the required fields to display errors from the api after a post call', async () => {
    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(true)

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // click the Save button
    wrapper.find('#ar-file-pay-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    expect(vm.saveErrorDialog).toBe(true)
    expect(vm.saveErrors.length).toBe(1)
    expect(vm.saveErrors[0].error).toBe('err msg post')
    expect(vm.saveWarnings.length).toBe(1)
    expect(vm.saveWarnings[0].warning).toBe('warn msg post')
  })

  it('sets the required fields to display errors from the api after a put call', async () => {
    // make sure form is validated
    vm.agmDateValid = true
    vm.addressesFormValid = true
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // confirm that flags are set correctly
    expect(vm.validated).toEqual(true)

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }
    // set the filingId
    vm.filingId = 123
    // click the Save button
    wrapper.find('#ar-file-pay-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    expect(vm.saveErrorDialog).toBe(true)
    expect(vm.saveErrors.length).toBe(1)
    expect(vm.saveErrors[0].error).toBe('err msg put')
    expect(vm.saveWarnings.length).toBe(1)
    expect(vm.saveWarnings[0].warning).toBe('warn msg put')
  })
})
