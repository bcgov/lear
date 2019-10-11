/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'
import { createLocalVue, shallowMount, mount } from '@vue/test-utils'
import flushPromises from 'flush-promises'
import Certify from '@/components/AnnualReport/Certify.vue'
import axios from '@/axios-auth'
import store from '@/store/store'
import StandaloneDirectorsFiling from '@/views/StandaloneDirectorsFiling.vue'
import Directors from '@/components/AnnualReport/Directors.vue'
import VueRouter from 'vue-router'
import mockRouter from './mockRouter'
import { BAD_REQUEST } from 'http-status-codes'

Vue.use(Vuetify)
Vue.use(Vuelidate)
// suppress update watchers warnings
// ref: https://github.com/vuejs/vue-test-utils/issues/532
Vue.config.silent = true

let vuetify = new Vuetify({})

const sampleDirectors = [
  {
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
  })

  it('renders the filing sub-components properly', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })

    expect(wrapper.find(Directors).exists()).toBe(true)
    expect(wrapper.find(Certify).exists()).toBe(true)

    wrapper.destroy()
  })

  it('enables Validated flag when sub-component flags are valid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // set stub list of filings
    vm.filingData.push({})

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(true)

    wrapper.destroy()
  })

  it('disables Validated flag when Directors form is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = false
    vm.certifyFormValid = true

    // set stub list of filings
    vm.filingData.push({})

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when Certify form is invalid', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = true
    vm.certifyFormValid = false

    // set stub list of filings
    vm.filingData.push({})

    // confirm that flag is set correctly
    expect(vm.validated).toEqual(false)

    wrapper.destroy()
  })

  it('disables Validated flag when no filing changes were made (ie: nothing to file)', () => {
    const $route = { params: { id: 0 } } // new filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route }, vuetify })
    const vm: any = wrapper.vm

    // set flags
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // set stub list of filings
    vm.filingData = []

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
    const vm: any = wrapper.vm

    // set flag
    vm.directorFormValid = true
    vm.certifyFormValid = true

    // set stub list of filings
    vm.filingData.push({})

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
    const vm: any = wrapper.vm
    // set flag
    vm.directorFormValid = true
    vm.certifyFormValid = false

    // set stub list of filings
    vm.filingData.push({})

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

  it('fetches a draft Standalone Directors filing', done => {
    const $route = { params: { id: '123' } } // draft filing id
    const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      // verify that Certified By was restored
      expect(vm.certifiedBy).toBe('Full Name')
      expect(vm.isCertified).toBe(false)

      // verify that we stored the Filing ID
      expect(+vm.filingId).toBe(123)

      // FUTURE - verify that changed directors were restored

      wrapper.destroy()
      done()
    })
  })
})

describe('Standalone Directors Filing - Part 3 - Submitting', () => {
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
      vm.directorFormValid = true
      vm.certifyFormValid = true
      vm.filingData = [{}] // dummy data
      expect(vm.validated).toEqual(true)

      // sanity check
      expect(jest.isMockFunction(window.location.assign)).toBe(true)

      // TODO: verify that new filing was created

      const button = wrapper.find('#cod-file-pay-btn')
      expect(button.attributes('disabled')).toBeUndefined()

      // click the File & Pay button
      button.trigger('click')
      // work-around because click trigger isn't working
      expect(await vm.onClickFilePay()).toBe(true)
      await flushPromises()

      // verify v-tooltip text - Todo - Tool tip is outside the wrapper. Yet to find out how to get hold of that.
      // const tooltipText = wrapper.find('#cod-file-pay-btn + span').text()
      // expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
      // expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

      // verify redirection
      const payURL = '/makepayment/321/' + encodeURIComponent('/cooperatives/dashboard?filing_id=123')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
    }
  )

  it('updates an existing filing and redirects to Pay URL when this is a draft filing and the ' +
    'File & Pay button is clicked',
  async () => {
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '123' } }) // new filing id
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
    vm.directorFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data
    expect(vm.validated).toEqual(true)

    // sanity check
    expect(jest.isMockFunction(window.location.assign)).toBe(true)

    // TODO: verify that draft filing was fetched

    const button = wrapper.find('#cod-file-pay-btn')
    expect(button.attributes('disabled')).toBeUndefined()

    // click the File & Pay button
    button.trigger('click')
    // work-around because click trigger isn't working
    expect(await vm.onClickFilePay()).toBe(true)

    // verify v-tooltip text - To find out how to get the tool tip text outside the wrapper
    // const tooltipText = wrapper.find('#cod-file-pay-btn + span').text()
    // expect(tooltipText).toContain('Ensure all of your information is entered correctly before you File & Pay.')
    // expect(tooltipText).toContain('There is no opportunity to change information beyond this point.')

    // verify redirection
    const payURL = '/makepayment/321/' + encodeURIComponent('/cooperatives/dashboard?filing_id=123')
    expect(window.location.assign).toHaveBeenCalledWith(payURL)

    wrapper.destroy()
  })

  it('disables File & Pay button if user has \'staff\' role', async () => {
    // init store
    store.state.keycloakRoles = ['staff']

    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'standalone-directors', params: { id: '123' } }) // new filing id
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
    vm.directorFormValid = true
    vm.certifyFormValid = true
    vm.filingData = [{}] // dummy data
    expect(vm.validated).toEqual(true)

    // verify that onClickFilePay() does nothing
    expect(await vm.onClickFilePay()).toBe(false)

    // verify v-tooltip text
    // Commented out because tool tip text is outside the wrapper. Need to figure out how to get hold of that.
    // expect(wrapper.find('#cod-file-pay-btn + span').text()).toBe('Staff are not allowed to file.')

    store.state.keycloakRoles = [] // cleanup

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
      const wrapper = shallowMount(StandaloneDirectorsFiling, { store, mocks: { $route } })
      const vm = wrapper.vm as any

      // make sure form is validated
      vm.directorFormValid = true
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
    vm.directorFormValid = true
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
    vm.directorFormValid = true
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

  it('sets the required fields to display errors from the api after a post call',
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
      vm.directorFormValid = true
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

  it('sets the required fields to display errors from the api after a put call',
    async () => {
      const localVue = createLocalVue()
      localVue.use(VueRouter)
      const router = mockRouter.mock()
      router.push({ name: 'standalone-directors', params: { id: '123' } }) // new filing id
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
      vm.directorFormValid = true
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
