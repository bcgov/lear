import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'
import { mount } from '@vue/test-utils'
import { EntityTypes } from '@/enums';

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

  it('displays registered office data when a Coop', done => {
    // Init Store
    store.state.registeredAddress = {
      'deliveryAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'UK'
        },
      'mailingAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'UK'
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
        '.address-panel .address-info li:nth-child(3)').textContent).toContain('UK')

      wrapper.destroy()
      done()
    })
  })

  it('displays registered address and records address data when a Bcorp', async done => {
    // Init Store
    store.state.entityType = EntityTypes.BCorp
    store.state.registeredAddress = {
      'deliveryAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'UK'
        },
      'mailingAddress':
        {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'UK'
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
          'streetAddress': '321 Burrard St',
          'addressCity': 'Vancouver',
          'addressRegion': 'BC',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'Ca'
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
        '.address-panel .address-info li:nth-child(3)').textContent).toContain('UK')

      expect(vm.$el.querySelector(
        '.address-panel:nth-child(2) .address-info').textContent).toContain('Victoria')
      expect(vm.$el.querySelector(
        '.address-panel:nth-child(2) .address-info li:nth-child(3)').textContent).toContain('CA')

      wrapper.destroy()
      done()
    })
  })
})
