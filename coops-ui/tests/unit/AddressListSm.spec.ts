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

    Vue.nextTick(async () => {
      expect(vm.registeredAddress).toBeNull()
      expect(vm.recordsAddress).toBeNull()

      wrapper.destroy()
      done()
    })
  })

  it('displays registered office data when a COOP', done => {
    // Init Store
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
          'streetAddress': '202 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }
    store.state.recordsAddress = null

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeNull()
      expect(vm.$el.querySelector(
        '.address-panel .address-info').textContent).toContain('Glasgow')
      expect(vm.$el.querySelector(
        '.address-panel .address-info li:nth-child(4)').textContent).toContain('Canada')
      expect(vm.$el.querySelector('#same-as-above')).toBeNull()

      wrapper.destroy()
      done()
    })
  })

  it('displays registered office and same as above text data when a COOP', done => {
    // Init Store
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

    Vue.nextTick(async () => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeNull()
      expect(vm.$el.querySelector(
        '.address-panel .address-info').textContent).toContain('Glasgow')
      expect(vm.$el.querySelector(
        '.address-panel .address-info li:nth-child(4)').textContent).toContain('Canada')
      expect(vm.$el.querySelector('.same-as-above').textContent).toContain('Same as above')

      wrapper.destroy()
      done()
    })
  })

  it('displays registered address and records address data when a BCORP', async done => {
    // Init Store
    store.state.entityType = EntityTypes.BCORP
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
          'streetAddress': '1234 Cloverdale St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'CA'
        }
    }

    const wrapper = mount(AddressListSm, { store, vuetify })
    const vm = wrapper.vm as any

    // Click the records office tab to display the addresses
    const button = vm.$el.querySelector('#record-office-panel')
    await button.click()

    Vue.nextTick(async () => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeDefined()

      expect(vm.$el.querySelector(
        '.address-panel .address-info').textContent).toContain('Glasgow')
      expect(vm.$el.querySelector(
        '.address-panel .address-info li:nth-child(4)').textContent).toContain('Canada')
      expect(vm.$el.querySelector('.address-panel .same-as-above')
        .textContent).toContain('Same as above')
      expect(vm.$el.querySelector(
        '.address-panel:nth-child(2) .address-info').textContent).toContain('Victoria')
      expect(vm.$el.querySelector(
        '.address-panel:nth-child(2) .address-info li:nth-child(4)')
        .textContent).toContain('Canada')
      expect(vm.$el.querySelector('.address-panel:nth-child(2) .same-as-above:nth-child(2)')).toBeNull()

      wrapper.destroy()
      done()
    })
  })

  it('displays records address and same as above text  data when a BCORP', async done => {
    // Init Store
    store.state.entityType = EntityTypes.BCORP
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
    const button = vm.$el.querySelector('#record-office-panel')
    await button.click()

    Vue.nextTick(async () => {
      expect(vm.registeredAddress).toBeDefined()
      expect(vm.recordsAddress).toBeDefined()

      expect(vm.$el.querySelector(
        '.address-panel .address-info').textContent).toContain('Glasgow')
      expect(vm.$el.querySelector(
        '.address-panel .address-info li:nth-child(4)').textContent).toContain('Canada')
      expect(vm.$el.querySelector('.address-panel .same-as-above')
        .textContent).toContain('Same as above')
      expect(vm.$el.querySelector(
        '.address-panel:nth-child(2) .address-info').textContent).toContain('Victoria')
      expect(vm.$el.querySelector(
        '.address-panel:nth-child(2) .address-info li:nth-child(4)')
        .textContent).toContain('Canada')
      expect(vm.$el.querySelector('.address-panel:nth-child(2) .same-as-above')
        .textContent).toContain('Same as above')

      wrapper.destroy()
      done()
    })
  })
})
