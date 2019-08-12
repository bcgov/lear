import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { shallowMount } from '@vue/test-utils'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import StandaloneDirectorsFiling from '@/views/StandaloneDirectorsFiling.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import Certify from '@/components/AnnualReport/Certify.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('Standalone Directors Filing - Part 1', () => {
  beforeEach(() => {
    // init store
    store.state.corpNum = 'CP0001191'
  })

  it('renders the filing sub-components properly', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })

    expect(wrapper.find(Directors).exists()).toBe(true)
    expect(wrapper.find(Certify).exists()).toBe(true)
  })

  it('enables Validated flag when sub-component flags are valid', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = true
    vm.changeCertifyData(true)

    // set stub list of filings
    vm.filingData.push({})

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(true)
  })

  it('disables Validated flag when Directors form is invalid', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = false
    vm.changeCertifyData(true)

    // set stub list of filings
    vm.filingData.push({})

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('disables Validated flag when Certify form is invalid', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = true
    vm.changeCertifyData(false)

    // set stub list of filings
    vm.filingData.push({})

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('disables Validated flag when no filing changes were made (ie: nothing to file)', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = true
    vm.changeCertifyData(true)

    // set stub list of filings
    vm.filingData = []

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('enables File & Pay button when Validated is true', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flag
    vm.directorFormValid = true
    vm.changeCertifyData(true)

    // set stub list of filings
    vm.filingData.push({})

    // confirm that button is enabled
    expect(wrapper.find('#cod-file-pay-btn').attributes('disabled')).not.toBe('true')
  })

  it('disables File & Pay button when Validated is false', () => {
    const $route = { params: { id: 0 } }
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set flag
    vm.directorFormValid = true
    vm.changeCertifyData(false)

    // set stub list of filings
    vm.filingData.push({})

    // confirm that button is disabled
    expect(wrapper.find('#cod-file-pay-btn').attributes('disabled')).toBe('true')
  })
})

describe('Standalone Directors Filing - Part 2', () => {
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

    const sampleDirectors = [
      {
        'officer': {
          'firstName': 'Peter',
          'middleInitial': null,
          'lastName': 'Griffin'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line one',
          'streetAddressAdditional': null,
          'addressCity': 'mailing_address city',
          'addressCountry': 'mailing_address country',
          'postalCode': 'H0H0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': null
        },
        'title': null,
        'appointmentDate': '2015-10-11',
        'cessationDate': null
      },
      {
        'officer': {
          'firstName': 'Joe',
          'middleInitial': 'P',
          'lastName': 'Swanson'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line #1',
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

    // mock "fetch a draft filing" endpoint
    sinon.stub(axios, 'get').withArgs('CP0001191/filings/123')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': sampleDirectors,
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
                'name': 'changeOfDirectors',
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
              'changeOfDirectors': {
                'directors': sampleDirectors,
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
                'name': 'changeOfDirectors',
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
              'changeOfDirectors': {
                'directors': sampleDirectors,
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
                'name': 'changeOfDirectors',
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
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.directorFormValid = true
      vm.changeCertifyData(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the File & Pay button
      wrapper.find('#cod-file-pay-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickFilePay()

      // verify redirection
      const payURL = '/makepayment/321/' + encodeURIComponent('/Dashboard?filing_id=123')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)
    }
  )

  it('updates an existing filing and redirects to Pay URL when this is a draft filing and the ' +
    'File & Pay button is clicked',
  async () => {
    const $route = { params: { id: 123 } } // draft filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    // make sure form is validated
    vm.directorFormValid = true
    vm.changeCertifyData(true)

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // TODO: verify that draft filing was fetched

    // click the File & Pay button
    wrapper.find('#cod-file-pay-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickFilePay()

    // verify redirection
    const payURL = '/makepayment/321/' + encodeURIComponent('/Dashboard?filing_id=123')
    expect(window.location.assign).toHaveBeenCalledWith(payURL)
  }
  )
})

describe('Standalone Directors Filing - Part 3', () => {
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

    const sampleDirectors = [
      {
        'officer': {
          'firstName': 'Peter',
          'middleInitial': null,
          'lastName': 'Griffin'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line one',
          'streetAddressAdditional': null,
          'addressCity': 'mailing_address city',
          'addressCountry': 'mailing_address country',
          'postalCode': 'H0H0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': null
        },
        'title': null,
        'appointmentDate': '2015-10-11',
        'cessationDate': null
      },
      {
        'officer': {
          'firstName': 'Joe',
          'middleInitial': 'P',
          'lastName': 'Swanson'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line #1',
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

    // mock "save draft" endpoint
    sinon.stub(axios, 'post').withArgs('CP0001191/filings?draft=true')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'filing': {
              'changeOfDirectors': {
                'directors': sampleDirectors,
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
                'name': 'changeOfDirectors',
                'date': '2017-06-06',
                'submitter': 'cp0001191',
                'status': 'DRAFT',
                'filingId': 123
              }
            }
          }
      })))
  })

  afterEach(() => {
    sinon.restore()
  })

  it('saves a new filing when this is a new AR and the Save button is clicked',
    async () => {
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.directorFormValid = true
      vm.changeCertifyData(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the Save button
      wrapper.find('#cod-save-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickSave()

      // verify no redirection
      expect(window.location.assign).not.toHaveBeenCalled()
    }
  )

  it('saves a new filing and redirects to Home URL when this is a new filing and the Save & Resume button is clicked',
    async () => {
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.directorFormValid = true
      vm.changeCertifyData(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the Save & Resume Later button
      wrapper.find('#cod-save-resume-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickSaveResume()

      // verify redirection
      const homeURL = ''
      expect(window.location.assign).toHaveBeenCalledWith(homeURL)
    }
  )
})
