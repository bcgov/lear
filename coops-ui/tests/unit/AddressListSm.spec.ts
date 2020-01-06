import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'
import { mount } from '@vue/test-utils'
import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

describe('AddressListSm', () => {
  it('handles empty data', done => {
    // init store
    store.state.registeredAddress = null
    store.state.recordsAddress = null

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.registeredAddress).toBeNull()
      expect(vm.recordsAddress).toBeNull()

      wrapper.destroy()
      done()
    })
  })

  it('displays all addresses when a COOP', done => {
    // Init Store
    store.state.entityType = EntityTypes.COOP
    store.state.registeredAddress = {
      'deliveryAddress':
        {
          'streetAddress': '111 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        },
      'mailingAddress':
        {
          'streetAddress': '222 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }
    store.state.recordsAddress = null

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeNull()

      // verify registered addresses
      expect(vm.$el.querySelector('#registered-office-panel .delivery-address-list-item .address-subtitle')
        .textContent).toContain('111 Buchanan St')
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .same-as-above'))
        .toBeNull()
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .address-subtitle')
        .textContent).toContain('222 Buchanan St')

      wrapper.destroy()
      done()
    })
  })

  it('displays "same as above" when a COOP', done => {
    // Init Store
    store.state.entityType = EntityTypes.COOP
    store.state.registeredAddress = {
      'deliveryAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        },
      'mailingAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }
    store.state.recordsAddress = null

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeNull()

      // verify registered addresses
      expect(vm.$el.querySelector('#registered-office-panel .delivery-address-list-item .address-subtitle')
        .textContent).toContain('220 Buchanan St')
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .same-as-above')
        .textContent).toContain('Same as above')
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .address-subtitle'))
        .toBeNull()

      wrapper.destroy()
      done()
    })
  })

  it('displays all addresses when a BCOMP', async done => {
    // Init Store
    store.state.entityType = EntityTypes.BCOMP
    store.state.registeredAddress = {
      'deliveryAddress':
        {
          'streetAddress': '111 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        },
      'mailingAddress':
        {
          'streetAddress': '222 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }
    store.state.recordsAddress = {
      'deliveryAddress':
        {
          'streetAddress': '123 Cloverdale St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'V8X 2T5',
          'addressCountry': 'CA'
        },
      'mailingAddress':
        {
          'streetAddress': '456 Cloverdale St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'V8X 2T5',
          'addressCountry': 'CA'
        }
    }

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    // Click the records office tab to display the addresses
    const button = vm.$el.querySelector('#records-office-panel-toggle')
    await button.click()

    Vue.nextTick(() => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeDefined()

      // verify registered addresses
      expect(vm.$el.querySelector('#registered-office-panel .delivery-address-list-item .address-subtitle')
        .textContent).toContain('111 Buchanan St')
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .same-as-above'))
        .toBeNull()
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .address-subtitle')
        .textContent).toContain('222 Buchanan St')

      // verify records addresses
      expect(vm.$el.querySelector('#records-office-panel .delivery-address-list-item .address-subtitle')
        .textContent).toContain('123 Cloverdale St')
      expect(vm.$el.querySelector('#records-office-panel .mailing-address-list-item .same-as-above'))
        .toBeNull()
      expect(vm.$el.querySelector('#records-office-panel .mailing-address-list-item .address-subtitle')
        .textContent).toContain('456 Cloverdale St')

      wrapper.destroy()
      done()
    })
  })

  it('displays "same as above" when a BCOMP', async done => {
    // Init Store
    store.state.entityType = EntityTypes.BCOMP
    store.state.registeredAddress = {
      'deliveryAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        },
      'mailingAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }
    store.state.recordsAddress = {
      'deliveryAddress':
        {
          'streetAddress': '123 Cloverdale St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        },
      'mailingAddress':
        {
          'streetAddress': '123 Cloverdale St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    // Click the records office tab to display the addresses
    const button = vm.$el.querySelector('#records-office-panel-toggle')
    await button.click()

    Vue.nextTick(() => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeDefined()

      // verify registered addresses
      expect(vm.$el.querySelector('#registered-office-panel .delivery-address-list-item .address-subtitle')
        .textContent).toContain('220 Buchanan St')
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .same-as-above')
        .textContent).toContain('Same as above')
      expect(vm.$el.querySelector('#registered-office-panel .mailing-address-list-item .address-subtitle'))
        .toBeNull()

      // verify records addresses
      expect(vm.$el.querySelector('#records-office-panel .delivery-address-list-item .address-subtitle')
        .textContent).toContain('123 Cloverdale St')
      expect(vm.$el.querySelector('#records-office-panel .mailing-address-list-item .same-as-above')
        .textContent).toContain('Same as above')
      expect(vm.$el.querySelector('#records-office-panel .mailing-address-list-item .address-subtitle'))
        .toBeNull()

      wrapper.destroy()
      done()
    })
  })
})
