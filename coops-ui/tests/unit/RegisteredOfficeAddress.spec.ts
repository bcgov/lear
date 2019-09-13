
import Vue from 'vue'
import Vuelidate from 'vuelidate'
import Vuetify from 'vuetify'
import flushPromises from 'flush-promises'
import sinon from 'sinon'
import { mount, Wrapper } from '@vue/test-utils'

import axios from '@/axios-auth'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('RegisteredOfficeAddress', () => {
  beforeAll(() => {
    // API call to get current addresses
    sinon.stub(axios, 'get').withArgs('CP0001191/addresses')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'mailingAddress': {
              'addressCity': 'Test City',
              'addressCountry': 'TA',
              'addressRegion': 'BC',
              'addressType': 'mailing',
              'deliveryInstructions': null,
              'postalCode': 'T3S3T3',
              'streetAddress': 'CP0001191-mailingAddress-Test Street',
              'streetAddressAdditional': null
            },
            'deliveryAddress': {
              'addressCity': 'Test City',
              'addressCountry': 'TA',
              'addressRegion': 'BC',
              'addressType': 'mailing',
              'deliveryInstructions': null,
              'postalCode': 'T3S3T3',
              'streetAddress': 'CP0001191-deliveryAddress-Test Street',
              'streetAddressAdditional': null
            }
          }
      })))
  })

  afterAll(() => {
    sinon.restore()
  })

  // draft addresses passed in from parent page
  const draftAddresses = {
    'mailingAddress': {
      'addressCity': 'Test City',
      'addressCountry': 'TA',
      'addressRegion': 'BC',
      'addressType': 'mailing',
      'deliveryInstructions': 'draft',
      'postalCode': 'T3S3T3',
      'streetAddress': '3333 Test Street',
      'streetAddressAdditional': null
    },
    'deliveryAddress': {
      'addressCity': 'Test City',
      'addressCountry': 'TA',
      'addressRegion': 'BC',
      'addressType': 'mailing',
      'deliveryInstructions': 'draft',
      'postalCode': 'T3S3T3',
      'streetAddress': '4444 Test Street',
      'streetAddressAdditional': null
    }
  }

  // TODO: too tightly-coupled to the internal workings of the component. Wait for it to be refactored to support the
  // v-model and then re-write this using the prop. Also gets rid of code needed to mock the API call.
  it('loads the current addresses properly', async () => {
    // Note: due to a sync mode change, the following sync workaround is required
    // ref: https://github.com/vuejs/vue-test-utils/issues/1130
    const wrapper: Wrapper<RegisteredOfficeAddress> = mount(RegisteredOfficeAddress, {
      sync: false,
      propsData: { legalEntityNumber: 'CP0001191' }
    })

    await flushPromises()

    const deliveryAddress: object = wrapper.vm['deliveryAddress']
    expect(deliveryAddress['streetAddress']).toEqual('CP0001191-deliveryAddress-Test Street')
    expect(deliveryAddress['streetAddressAdditional']).toBeNull()
    expect(deliveryAddress['addressCity']).toEqual('Test City')
    expect(deliveryAddress['addressRegion']).toEqual('BC')
    expect(deliveryAddress['postalCode']).toEqual('T3S3T3')
    expect(deliveryAddress['addressCountry']).toEqual('TA')
    expect(deliveryAddress['deliveryInstructions']).toBeNull()

    const mailingAddress: object = wrapper.vm['mailingAddress']
    expect(mailingAddress['streetAddress']).toEqual('CP0001191-mailingAddress-Test Street')
    expect(mailingAddress['streetAddressAdditional']).toBeNull()
    expect(mailingAddress['addressCity']).toEqual('Test City')
    expect(mailingAddress['addressRegion']).toEqual('BC')
    expect(mailingAddress['postalCode']).toEqual('T3S3T3')
    expect(mailingAddress['addressCountry']).toEqual('TA')
    expect(mailingAddress['deliveryInstructions']).toBeNull()

    wrapper.destroy()
  })

  it('loads the draft addresses properly', async () => {
    const wrapper: Wrapper<RegisteredOfficeAddress> = mount(RegisteredOfficeAddress, {
      sync: false,
      propsData: { legalEntityNumber: 'CP0001191', addresses: null }
    })

    await flushPromises()

    // simulate parent asynchronously loading a draft filing
    wrapper.setProps({ addresses: draftAddresses })

    // verify that property was set properly
    expect(wrapper.vm['addresses']['deliveryAddress'].streetAddress).toEqual('4444 Test Street')
    expect(wrapper.vm['addresses']['deliveryAddress'].deliveryInstructions).toEqual('draft')
    expect(wrapper.vm['addresses']['mailingAddress'].streetAddress).toEqual('3333 Test Street')
    expect(wrapper.vm['addresses']['mailingAddress'].deliveryInstructions).toEqual('draft')

    // call addresses watcher (since setProps() apparently doesn't call it in a TS component)
    // see: https://github.com/vuejs/vue-test-utils/issues/255#issuecomment-408810553
    await (wrapper.vm as any).onAddressesChanged()

    // verify that current delivery address was updated by property watcher
    const deliveryAddress: object = wrapper.vm['deliveryAddress']
    expect(deliveryAddress['streetAddress']).toEqual('4444 Test Street')
    expect(deliveryAddress['deliveryInstructions']).toEqual('draft')

    // verify that current mailing address was updated by property watcher
    const mailingAddress: object = wrapper.vm['mailingAddress']
    expect(mailingAddress['streetAddress']).toEqual('3333 Test Street')
    expect(mailingAddress['deliveryInstructions']).toEqual('draft')

    wrapper.destroy()
  })

  it('has enabled Change button', () => {
    const wrapper: Wrapper<RegisteredOfficeAddress> = mount(RegisteredOfficeAddress, {
      sync: false,
      propsData: { changeButtonDisabled: false }
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeUndefined()

    wrapper.destroy()
  })

  it('has disabled Change button', () => {
    const wrapper: Wrapper<RegisteredOfficeAddress> = mount(RegisteredOfficeAddress, {
      sync: false,
      propsData: { changeButtonDisabled: true }
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBe('disabled')

    wrapper.destroy()
  })
})
