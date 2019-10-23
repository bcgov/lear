import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import VueRouter from 'vue-router'
import { mount, shallowMount, createLocalVue } from '@vue/test-utils'

import mockRouter from './mockRouter'
import store from '@/store/store'
import Dashboard from '@/views/Dashboard.vue'
import TodoList from '@/components/Dashboard/TodoList.vue'
import FilingHistoryList from '@/components/Dashboard/FilingHistoryList.vue'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'
import DirectorListSm from '@/components/Dashboard/DirectorListSm.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('Dashboard - UI', () => {
  let wrapper

  beforeEach(() => {
    // create wrapper for Dashboard
    // this stubs out the 4 sub-components
    wrapper = shallowMount(Dashboard, { vuetify })
  })

  afterEach(() => {
    wrapper.destroy()
  })

  it('renders the dashboard sub-components properly', () => {
    expect(wrapper.find(TodoList).exists()).toBe(true)
    expect(wrapper.find(FilingHistoryList).exists()).toBe(true)
    expect(wrapper.find(AddressListSm).exists()).toBe(true)
    expect(wrapper.find(DirectorListSm).exists()).toBe(true)
  })

  it('updates its counts from sub-component events', () => {
    wrapper.find(TodoList).vm.$emit('todo-count', 2)
    wrapper.find(FilingHistoryList).vm.$emit('filed-count', 3)

    expect(wrapper.vm.todoCount).toEqual(2)
    expect(wrapper.vm.filedCount).toEqual(3)
  })

  it('enables standalone filing buttons when there are no blocker filings in the to-do list', () => {
    wrapper.find(TodoList).vm.$emit('has-blocker-filing', false)

    expect(wrapper.vm.hasBlockerFiling).toEqual(false)
    expect(wrapper.vm.$el.querySelector('#btn-standalone-addresses')
      .getAttribute('disabled')).toBeFalsy()
    expect(wrapper.vm.$el.querySelector('#btn-standalone-directors')
      .getAttribute('disabled')).toBeFalsy()
  })

  it('disables standalone filing buttons when there is a blocker filing in the to-do list', () => {
    wrapper.find(TodoList).vm.$emit('has-blocker-filing', true)

    expect(wrapper.vm.hasBlockerFiling).toEqual(true)
    expect(wrapper.vm.$el.querySelector('#btn-standalone-addresses')
      .getAttribute('disabled')).toBeTruthy()
    expect(wrapper.vm.$el.querySelector('#btn-standalone-directors')
      .getAttribute('disabled')).toBeTruthy()
  })

  it('marks filing as PROCESSING when expecting completed filing and dashboard does not reflect this', () => {
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'dashboard', query: { filing_id: '123' } })
    const wrapper = mount(Dashboard, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    // push filing ID in URL to indicate that we've returned from the dashboard from a filing (file pay, not save draft)
    expect(vm.$route.query.filing_id).toBe('123')

    // emit to-do list from to-do component with the filing marked as pending
    wrapper.find(TodoList).vm.$emit('todo-filings', [
      {
        'type': 'changeOfDirectors',
        'id': 123,
        'status': 'PENDING',
        'enabled': true,
        'order': 1
      }])

    // emit filing list from Filing History component without the completed filing
    wrapper.find(FilingHistoryList).vm.$emit('filings-list', [])

    expect(vm.inProcessFiling).toEqual(123)
  })

  it('does not mark filing as PROCESSING when expecting completed filing and dashboard reflects this', () => {
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    router.push({ name: 'dashboard', query: { filing_id: '123' } })
    const wrapper = mount(Dashboard, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    // push filing ID in URL to indicate that we've returned from the dashboard from a filing (file pay, not save draft)
    expect(vm.$route.query.filing_id).toBe('123')

    // emit to-do list from to-do component without the filing marked as pending
    wrapper.find(TodoList).vm.$emit('todo-filings', [])

    // emit filing list from Filing History component with the completed filing
    wrapper.find(FilingHistoryList).vm.$emit('filings-list', [
      {
        'name': 'Director Change',
        'filingId': 123,
        'filingAuthor': 'fS',
        'filingDate': '2019-10-17',
        'paymentToken': '661'
      }
    ])

    expect(vm.inProcessFiling).toBeNull()
  })
})

describe('Dashboard - Click Tests', () => {
  it('routes to Standalone Office Address Filing page when EDIT is clicked', done => {
    // init store
    store.state.entityIncNo = 'CP0001191'

    // create a Local Vue and install router on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    const wrapper = mount(Dashboard, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = vm.$el.querySelector('#btn-standalone-addresses')
      expect(button.querySelector('.v-btn__content').textContent).toContain('Change')
      await button.click()

      // verify routing to Standalone Office Address Filing page with id=0
      expect(vm.$route.name).toBe('standalone-addresses')
      expect(vm.$route.params.id).toBe(0)

      wrapper.destroy()
      done()
    })
  })

  it('routes to Standalone Directors Filing page when EDIT is clicked', done => {
    // init store
    store.state.entityIncNo = 'CP0001191'

    // create a Local Vue and install router on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    const wrapper = mount(Dashboard, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = vm.$el.querySelector('#btn-standalone-directors')
      expect(button.querySelector('.v-btn__content').textContent).toContain('Change')
      await button.click()

      // verify routing to Standalone Directors Filing page with id=0
      expect(vm.$route.name).toBe('standalone-directors')
      expect(vm.$route.params.id).toBe(0)

      wrapper.destroy()
      done()
    })
  })
})
