import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { mount } from '@vue/test-utils'

import store from '@/store/store'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AddressListSm', () => {
  it('handles empty data', done => {
    // init store
    store.state.mailingAddress = null
    store.state.deliveryAddress = null

    const wrapper = mount(AddressListSm, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.mailingAddress).toBeNull()
      expect(vm.deliveryAddress).toBeNull()
      expect(vm.$el.querySelectorAll('.list-item').length).toEqual(0)

      wrapper.destroy()
      done()
    })
  })

  it('displays the mailing address', done => {
    // init store
    store.state.mailingAddress = {
      'streetAddress': '1012 Douglas St',
      'addressCity': 'Victoria',
      'addressRegion': 'BC',
      'postalCode': 'V8W 2C3',
      'addressCountry': 'CA'
    }
    store.state.deliveryAddress = null

    const wrapper = mount(AddressListSm, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.mailingAddress).not.toBeNull()
      expect(vm.deliveryAddress).toBeNull()
      expect(vm.$el.querySelectorAll('.list-item').length).toEqual(1)
      expect(vm.$el.querySelector('.list-item__title').textContent).toBe('Mailing Address')
      expect(vm.$el.querySelector('.address-details').textContent).toContain('Victoria BC')

      wrapper.destroy()
      done()
    })
  })

  it('displays the delivery address', done => {
    // init store
    store.state.mailingAddress = null
    store.state.deliveryAddress = {
      'streetAddress': '220 Buchanan St',
      'addressCity': 'Glasgow',
      'addressRegion': 'Scotland',
      'postalCode': 'G1 2FFF',
      'addressCountry': 'UK'
    }

    const wrapper = mount(AddressListSm, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.mailingAddress).toBeNull()
      expect(vm.deliveryAddress).not.toBeNull()
      expect(vm.$el.querySelectorAll('.list-item').length).toEqual(1)
      expect(vm.$el.querySelector('.list-item__title').textContent).toBe('Delivery Address')
      expect(vm.$el.querySelector('.address-details').textContent).toContain('Glasgow Scotland')

      wrapper.destroy()
      done()
    })
  })
})
