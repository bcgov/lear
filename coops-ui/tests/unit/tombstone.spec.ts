import Vue from 'vue'
import Vuetify from 'vuetify'

import Tombstone from '@/components/Tombstone.vue'
Vue.use(Vuetify)

describe('Tombstone.vue', () => {
  const Constructor = Vue.extend(Tombstone)
  let instance = new Constructor()
  let vm = instance.$mount()

  beforeEach((done) => {
    // clear data
    vm.$data.entityName = ''
    vm.$data.entityBusinessNo = ''
    vm.$data.entityIncNo = ''
    vm.$data.entityStatus = ''

    setTimeout(() => {
      done()
    }, 100)
  })

  afterEach((done) => {
    setTimeout(() => {
      done()
    }, 100)
  })

  it('shows all elements', () => {
    // set data
    vm.$data.entityName = 'My Business Name XYZ'
    vm.$data.entityBusinessNo = '123'
    vm.$data.entityIncNo = '456'
    vm.$data.entityStatus = 'PENDINGDISSOLUTION'

    setTimeout(() => {
      // expect business name, business no, incorp no, and status to be on the screen
      expect(vm.$el.querySelector('.entity-name').textContent).toEqual('My Business Name XYZ')
      expect(vm.$el.querySelector('.entity-status').textContent).toContain('Pending Dissolution')
      expect(vm.$el.querySelector('.business-number').textContent).toEqual('123')
      expect(vm.$el.querySelector('.incorp-number').textContent).toEqual('456')

    }, 10)
  })

  it('handles empty data', () => {
    expect(vm.$el.querySelector('.entity-name').textContent).toEqual('')
    expect(vm.$el.querySelector('.entity-status').textContent).toContain('')
    expect(vm.$el.querySelector('.business-number').textContent).toEqual('Not Available')
    expect(vm.$el.querySelector('.incorp-number').textContent).toEqual('Not Available')
  })
})
