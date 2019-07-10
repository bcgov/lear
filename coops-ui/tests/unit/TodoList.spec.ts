import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import TodoList from '@/components/Dashboard/TodoList.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('TodoList.vue', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.currentDate = '2019-07-12'
    store.state.lastAgmDate = '2017-04-08'

    const constructor = Vue.extend(TodoList)
    const instance = new constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  it('creates the Todo Items properly', () => {
    expect(vm.todoItems).not.toBeNull()
    expect(vm.todoItems.length).toEqual(2)
  })
})
