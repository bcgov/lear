import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AddressListSm.vue', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'

    // GET addresses
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
              'streetAddress': 'CP0002098-mailingAddress-Test Street',
              'streetAddressAdditional': null
            },
            'deliveryAddress': {
              'addressCity': 'Test City',
              'addressCountry': 'TA',
              'addressRegion': 'BC',
              'addressType': 'mailing',
              'deliveryInstructions': null,
              'postalCode': 'T3S3T3',
              'streetAddress': 'CP0002098-deliveryAddress-Test Street',
              'streetAddressAdditional': null
            }
          }
      })))

    const constructor = Vue.extend(AddressListSm)
    const instance = new constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('loads and displays the addresses properly', () => {
    expect(vm.mailingAddress).not.toBeNull()
    expect(vm.deliveryAddress).not.toBeNull()
  })
})
