import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import EntityInfo from '@/components/EntityInfo.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('EntityInfo.vue', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'

    // GET entity info
    sinon.stub(axios, 'get').withArgs('CP0001191')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            business: {
              foundingDate: '2001-08-05',
              identifier: 'CP0001191',
              legalName: 'test name - CP0001191',
              status: 'GOODSTANDING',
              taxId: '123456789'
            }
          }
      })))

    const constructor = Vue.extend(EntityInfo)
    let instance = new constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('gets and displays entity info properly', () => {
    expect(vm.$el.querySelector('.entity-name').textContent).toEqual('test name - CP0001191')
    expect(vm.$el.querySelector('.entity-status').textContent).toContain('In Good Standing')
    expect(vm.$el.querySelector('.business-number').textContent).toEqual('123456789')
    expect(vm.$el.querySelector('.incorp-number').textContent).toEqual('CP0001191')
  })

  it('handles empty data', done => {
    vm.$store.state.entityName = null
    vm.$store.state.entityStatus = null
    vm.$store.state.entityBusinessNo = null
    vm.$store.state.entityIncNo = null

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('.entity-name').textContent).toEqual('Not Available')
      expect(vm.$el.querySelector('.entity-status')).toBeNull()
      expect(vm.$el.querySelector('.business-number').textContent).toEqual('Not Available')
      expect(vm.$el.querySelector('.incorp-number').textContent).toEqual('Not Available')
      done()
    })
  })
})
