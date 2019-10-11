import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { mount } from '@vue/test-utils'

import store from '@/store/store'
import DirectorListSm from '@/components/Dashboard/DirectorListSm.vue'
import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

describe('DirectorListSm', () => {
  it('handles empty data as a coop', done => {
    // init store
    store.state.directors = []
    store.state.entityType = EntityTypes.Coop

    const wrapper = mount(DirectorListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.directors.length).toEqual(0)
      expect(vm.$el.querySelectorAll('.address-panel').length).toEqual(0)

      wrapper.destroy()
      done()
    })
  })

  it('displays multiple directors as a coop', done => {
    // init store
    store.state.entityType = EntityTypes.Coop
    store.state.directors = [
      {
        'officer': {
          'firstName': 'Peter',
          'lastName': 'Griffin'
        },
        'deliveryAddress': {
          'streetAddress': '1012 Douglas St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'V8W 2C3',
          'addressCountry': 'CA'
        }
      },
      {
        'officer': {
          'firstName': 'Joe',
          'lastName': 'Swanson'
        },
        'deliveryAddress': {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'UK'
        }
      }
    ]

    const wrapper = mount(DirectorListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.directors.length).toEqual(2)
      expect(vm.directors[0].mailingAddress).toBeUndefined()
      expect(vm.$el.querySelectorAll('.address-panel').length).toEqual(2)

      wrapper.destroy()
      done()
    })
  })

  it('handles empty data as a coop', done => {
    // init store
    store.state.directors = []
    store.state.entityType = EntityTypes.Coop

    const wrapper = mount(DirectorListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.directors.length).toEqual(0)
      expect(vm.directors.mailingAddress).toBeUndefined()
      expect(vm.$el.querySelectorAll('.address-panel').length).toEqual(0)

      wrapper.destroy()
      done()
    })
  })

  it('displays multiple directors as a bcorp', done => {
    // init store
    store.state.entityType = EntityTypes.BCorp
    store.state.directors = [
      {
        'officer': {
          'firstName': 'Peter',
          'lastName': 'Griffin'
        },
        'deliveryAddress': {
          'streetAddress': '1012 Douglas St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'V8W 2C3',
          'addressCountry': 'CA'
        },
        'mailingAddress': {
          'streetAddress': '1012 Douglas St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'V8W 2C3',
          'addressCountry': 'CA'
        }
      },
      {
        'officer': {
          'firstName': 'Joe',
          'lastName': 'Swanson'
        },
        'deliveryAddress': {
          'streetAddress': '220 Buchanan St',
          'addressCity': 'Glasgow',
          'addressRegion': 'Scotland',
          'postalCode': 'G1 2FFF',
          'addressCountry': 'UK'
        },
        'mailingAddress': {
          'streetAddress': '1012 Douglas St',
          'addressCity': 'Victoria',
          'addressRegion': 'BC',
          'postalCode': 'V8W 2C3',
          'addressCountry': 'CA'
        }
      }
    ]

    const wrapper = mount(DirectorListSm, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.directors.length).toEqual(2)
      expect(vm.directors[0].mailingAddress).toBeDefined()
      expect(vm.$el.querySelectorAll('.address-panel').length).toEqual(2)

      wrapper.destroy()
      done()
    })
  })
})
