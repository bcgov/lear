import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

describe('AddressListSm', () => {
  let vm

  beforeEach(done => {
    const Constructor = Vue.extend(AddressListSm)
    const instance = new Constructor({ store: store, vuetify })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  it('handles empty data', done => {
    // init store
    store.state.mailingAddress = null
    store.state.deliveryAddress = null

    Vue.nextTick(() => {
      expect(vm.mailingAddress).toBeNull()
      expect(vm.deliveryAddress).toBeNull()
      expect(vm.$el.querySelectorAll('.list-item').length).toEqual(0)

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

    Vue.nextTick(() => {
      expect(vm.mailingAddress).not.toBeNull()
      expect(vm.deliveryAddress).toBeNull()
      expect(vm.$el.querySelectorAll('.list-item').length).toEqual(1)
      expect(vm.$el.querySelector('.list-item__title').textContent).toBe('Mailing Address')
      expect(vm.$el.querySelector('.address-details').textContent).toContain('Victoria BC')

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

    Vue.nextTick(() => {
      expect(vm.mailingAddress).toBeNull()
      expect(vm.deliveryAddress).not.toBeNull()
      expect(vm.$el.querySelectorAll('.list-item').length).toEqual(1)
      expect(vm.$el.querySelector('.list-item__title').textContent).toBe('Delivery Address')
      expect(vm.$el.querySelector('.address-details').textContent).toContain('Glasgow Scotland')

      done()
    })
  })
})
