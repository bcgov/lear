import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import EntityInfo from '@/components/EntityInfo.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('EntityInfo', () => {
  let vm

  beforeEach(done => {
    const Constructor = Vue.extend(EntityInfo)
    const instance = new Constructor({ store, vuetify })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  it('displays entity info properly', done => {
    vm.$store.state.entityName = 'test name - CP0001191'
    vm.$store.state.entityStatus = 'GOODSTANDING'
    vm.$store.state.entityBusinessNo = '123456789'
    vm.$store.state.entityIncNo = 'CP0001191'

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#entity-legal-name').textContent).toEqual('test name - CP0001191')
      expect(vm.$el.querySelector('#entity-status').textContent).toContain('In Good Standing')
      expect(vm.$el.querySelector('#entity-business-number').textContent).toEqual('123456789')
      expect(vm.$el.querySelector('#entity-incorporation-number').textContent).toEqual('CP0001191')
      done()
    })
  })

  it('handles empty data', done => {
    vm.$store.state.entityName = null
    vm.$store.state.entityStatus = null
    vm.$store.state.entityBusinessNo = null
    vm.$store.state.entityIncNo = null

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#entity-legal-name').textContent).toEqual('Not Available')
      expect(vm.$el.querySelector('#entity-status')).toBeNull()
      expect(vm.$el.querySelector('#entity-business-number').textContent).toEqual('Not Available')
      expect(vm.$el.querySelector('#entity-incorporation-number').textContent).toEqual('Not Available')
      done()
    })
  })
})
