/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'
import { createLocalVue, shallowMount } from '@vue/test-utils'

import axios from '@/axios-auth'
import store from '@/store/store'
import StandaloneOfficeAddressFiling from '@/views/StandaloneOfficeAddressFiling.vue'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import VueRouter from 'vue-router'
import mockRouter from './mockRouter'
import { BAD_REQUEST } from 'http-status-codes'

Vue.use(Vuetify)
Vue.use(Vuelidate)

const sampleDeliveryAddress = {
  'streetAddress': 'delivery street address',
  'streetAddressAdditional': null,
  'addressCity': 'deliv address city',
  'addressCountry': 'deliv country',
  'postalCode': 'H0H0H0',
  'addressRegion': 'BC',
  'deliveryInstructions': null
}

const sampleMailingAddress = {
  'streetAddress': 'mailing street address',
  'streetAddressAdditional': 'Kirkintiloch',
  'addressCity': 'Glasgow',
  'addressCountry': 'UK',
  'postalCode': 'H0H 0H0',
  'addressRegion': 'Scotland',
  'deliveryInstructions': 'go to the back'
}

describe('Standalone Office Address Filing - Part 1 - UI', () => {
  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0001191'
  })

  it('renders the filing sub-components properly', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })

    expect(wrapper.find(RegisteredOfficeAddress).exists()).toBe(true)
    expect(wrapper.find(Certify).exists()).toBe(true)

    wrapper.destroy()
  })

  it('enables Validated flag when properties are valid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set properties
    vm.isCertified = true
    vm.officeAddressFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(true)

    wrapper.destroy()
  })

  it('disables Validated flag when Office Address form is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set properties
    vm.isCertified = true
    vm.officeAddressFormValid = false
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Certify form is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set properties
    vm.isCertified = false
    vm.officeAddressFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Certify form is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set properties
    vm.isCertified = true
    vm.officeAddressFormValid = true
    vm.filingData = []

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)
  })

  it('enables File & Pay button when Validated is true', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set all properties truthy
    vm.isCertified = true
    vm.officeAddressFormValid = true
    vm.filingData = [{}] // dummy data

    // confirm that button is enabled
    expect(wrapper.find('#coa-file-pay-btn').attributes('disabled')).not.toBe('true')

    wrapper.destroy()
  })

  it('disables File & Pay button when Validated is false', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm: any = wrapper.vm

    // set all properties falsy
    vm.isCertified = false
    vm.officeAddressFormValid = false
    vm.filingData = [] // dummy data

    // confirm that button is disabled
    expect(wrapper.find('#coa-file-pay-btn').attributes('disabled')).toBe('true')

    wrapper.destroy()
  })
})

describe('Standalone Office Address Filing - Part 2 - Resuming', () => {
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
              'changeOfAddress': {
                'deliveryAddress': sampleDeliveryAddress,
                'mailingAddress': sampleMailingAddress
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfAddress',
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

  it('fetches a draft Standalone Office Address filing', done => {
    const $route = { params: { id: '123' } } // draft filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      // verify that Certified By was restored
      expect(vm.certifiedBy).toBe('Full Name')
      expect(vm.isCertified).toBe(false)

      // verify that we stored the Filing ID
      expect(+vm.filingId).toBe(123)

      // verify that changed addresses were restored
      expect(vm.addresses.deliveryAddress.streetAddress).toBe('delivery street address')
      expect(vm.addresses.mailingAddress.streetAddress).toBe('mailing street address')

      wrapper.destroy()
      done()
    })
  })
})

describe('Standalone Office Address Filing - Part 3 - Submitting', () => {
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
              'changeOfAddress': {
                'deliveryAddress': sampleDeliveryAddress,
                'mailingAddress': sampleMailingAddress
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfAddress',
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
              'changeOfAddress': {
                'deliveryAddress': sampleDeliveryAddress,
                'mailingAddress': sampleMailingAddress
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfAddress',
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
              'changeOfAddress': {
                'deliveryAddress': sampleDeliveryAddress,
                'mailingAddress': sampleMailingAddress
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfAddress',
                'date': '2017-06-06',
                'submitter': 'cp0001191',
                'status': 'PENDING',
                'certifiedBy': 'Full Name',
                'email': 'no_one@never.get',
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
      const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.officeAddressFormValid = true
      vm.isCertified = true
      vm.filingData = [{}] // dummy data
      expect(vm.validated).toEqual(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      const button = wrapper.find('#coa-file-pay-btn')
      expect(button.attributes('disabled')).toBeUndefined()

      // click the File & Pay button
      button.trigger('click')
      // work-around because click trigger isn't working
      expect(await vm.onClickFilePay()).toBe(true)

      // verify v-tooltip text
      const tooltipText = wrapper.find('#coa-file-pay-btn + span').text()
      expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
      expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

      // verify redirection
      const payURL = '/makepayment/321/' + encodeURIComponent('/dashboard?filing_id=123')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
    }
  )

  it('updates an existing filing and redirects to Pay URL when this is a draft filing and the ' +
    'File & Pay button is clicked',
  async () => {
    const $route = { params: { id: 123 } } // draft filing id
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    // make sure form is validated
    vm.officeAddressFormValid = true
    vm.isCertified = true
    vm.filingData = [{}] // dummy data
    expect(vm.validated).toEqual(true)

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // TODO: verify that draft filing was fetched

    const button = wrapper.find('#coa-file-pay-btn')
    expect(button.attributes('disabled')).toBeUndefined()

    // click the File & Pay button
    button.trigger('click')
    // work-around because click trigger isn't working
    expect(await vm.onClickFilePay()).toBe(true)

    // verify v-tooltip text
    const tooltipText = wrapper.find('#coa-file-pay-btn + span').text()
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
    const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    // make sure form is validated
    vm.officeAddressFormValid = true
    vm.isCertified = true
    vm.filingData = [{}] // dummy data
    expect(vm.validated).toEqual(true)

    // verify that onClickFilePay() does nothing
    expect(await vm.onClickFilePay()).toBe(false)

    // verify v-tooltip text
    expect(wrapper.find('#coa-file-pay-btn + span').text()).toBe('Staff are not allowed to file.')

    store.state.keycloakRoles = [] // cleanup

    wrapper.destroy()
  })
})

describe('Standalone Office Address Filing - Part 4 - Saving', () => {
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
              'changeOfAddress': {
                'deliveryAddress': sampleDeliveryAddress,
                'mailingAddress': sampleMailingAddress
              },
              'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0001191',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0001191'
              },
              'header': {
                'name': 'changeOfAddress',
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

  it('saves a new filing when this is a new AR and the Save button is clicked',
    async () => {
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.officeAddressFormValid = true
      vm.isCertified = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the Save button
      wrapper.find('#coa-save-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickSave()

      // verify no redirection
      expect(window.location.assign).not.toHaveBeenCalled()

      wrapper.destroy()
    }
  )

  it('saves a new filing and redirects to Home URL when this is a new filing and the Save & Resume button is clicked',
    async () => {
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.officeAddressFormValid = true
      vm.isCertified = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the Save & Resume Later button
      wrapper.find('#coa-save-resume-btn').trigger('click')
      // work-around because click trigger isn't working
      await vm.onClickSaveResume()

      // verify redirection
      const homeURL = ''
      expect(window.location.assign).toHaveBeenCalledWith(homeURL)

      wrapper.destroy()
    }
  )
})

describe('Standalone Office Address Filing - Part 5 - Data', () => {
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
              'changeOfAddress': {
                'deliveryAddress': {},
                'mailingAddress': {}
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
    router.push({ name: 'standalone-addresses', params: { id: '0' } }) // new filing id

    wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, localVue, router })
    vm = wrapper.vm as any

    // stub address data
    vm.addresses = {
      'deliveryAddress': {},
      'mailingAddress': {}
    }

    // make sure form is validated
    vm.officeAddressFormValid = true
    vm.isCertified = true
    vm.officeModifiedEventHandler(true)
  })

  afterEach(() => {
    sinon.restore()
    wrapper.destroy()
  })

  it('Includes certification data in the header', async () => {
    // click the Save button
    wrapper.find('#coa-save-btn').trigger('click')
    // work-around because click trigger isn't working
    await vm.onClickSave()

    const payload = spy.args[0][1]

    // basic tests to pass ensuring structure of payload is as expected
    expect(payload.filing).toBeDefined()
    expect(payload.filing.changeOfAddress).toBeDefined()
    expect(payload.filing.header).toBeDefined()

    expect(payload.filing.header.certifiedBy).toBeDefined()
    expect(payload.filing.header.email).toBeDefined()
  })
})

describe('Standalone Office Address Filing - Part 6 - Error/Warning dialogues', () => {
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
            'changeOfAddress': {
              'deliveryAddress': sampleDeliveryAddress,
              'mailingAddress': sampleMailingAddress
            },
            'business': {
              'cacheId': 1,
              'foundingDate': '2007-04-08',
              'identifier': 'CP0001191',
              'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
              'legalName': 'Legal Name - CP0001191'
            },
            'header': {
              'name': 'changeOfAddress',
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
    p1.catch(() => {})
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
            'changeOfAddress': {
              'deliveryAddress': sampleDeliveryAddress,
              'mailingAddress': sampleMailingAddress
            },
            'business': {
              'cacheId': 1,
              'foundingDate': '2007-04-08',
              'identifier': 'CP0001191',
              'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
              'legalName': 'Legal Name - CP0001191'
            },
            'header': {
              'name': 'changeOfAddress',
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
    p2.catch(() => {})
    sinon.stub(axios, 'put').withArgs('CP0001191/filings/123').returns(p2)
  })

  afterEach(() => {
    sinon.restore()
  })

  it('sets the required fields to display errors from the api after a post call',
    async () => {
      const $route = { params: { id: 0 } } // new filing id
      const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.officeAddressFormValid = true
      vm.isCertified = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the File & Pay button
      wrapper.find('#coa-file-pay-btn').trigger('click')
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

  it('sets the required fields to display errors from the api after a put call',
    async () => {
      const $route = { params: { id: 123 } } // new filing id
      const wrapper = shallowMount(StandaloneOfficeAddressFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.officeAddressFormValid = true
      vm.isCertified = true

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      // click the File & Pay button
      wrapper.find('#coa-file-pay-btn').trigger('click')
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
