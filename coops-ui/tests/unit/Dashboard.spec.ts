import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { shallowMount } from '@vue/test-utils'

import Dashboard from '@/views/Dashboard.vue'
import TodoList from '@/components/Dashboard/TodoList.vue'
import FilingHistoryList from '@/components/Dashboard/FilingHistoryList.vue'
import AddressListSm from '@/components/Dashboard/AddressListSm.vue'
import DirectorListSm from '@/components/Dashboard/DirectorListSm.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('Dashboard.vue', () => {
  let wrapper

  beforeEach(() => {
    // create wrapper for Dashboard
    // this stubs out the 4 sub-components
    wrapper = shallowMount(Dashboard)
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
})
