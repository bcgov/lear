import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import VueRouter from 'vue-router'
import { mount, createLocalVue } from '@vue/test-utils'
import axios from '@/axios-auth'
import sinon from 'sinon'

import mockRouter from './mockRouter'
import store from '@/store/store'
import TodoList from '@/components/Dashboard/TodoList.vue'
import flushPromises from 'flush-promises'

// Enums
import { EntityTypes } from '@/enums'

// NB: test util async issue
// in some cases, the elements are not updated during the test
// the work-around is to first initialize the property we are changing
// suppress update watchers warnings
// ref: https://github.com/vuejs/vue-test-utils/issues/532
Vue.config.silent = true

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('TodoList - UI', () => {
  beforeAll(() => {
    store.state.entityType = EntityTypes.COOP
  })

  it('handles empty data', async () => {
    // init store
    store.state.tasks = []

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(0)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(0)
    expect(wrapper.emitted('todo-count')).toEqual([[0]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).not.toBeNull()
    expect(vm.$el.querySelector('.no-results').textContent).toContain('You don\'t have anything to do yet')

    wrapper.destroy()
  })

  it('displays multiple task items', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2017,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2017-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      },
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2018,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2018-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': false,
        'order': 2
      },
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2019-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': false,
        'order': 3
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(3)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(3)
    expect(wrapper.emitted('todo-count')).toEqual([[3]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    // verify that first task is enabled and other 2 are disabled
    const item1 = vm.$el.querySelectorAll('.todo-item')[0]
    const item2 = vm.$el.querySelectorAll('.todo-item')[1]
    const item3 = vm.$el.querySelectorAll('.todo-item')[2]

    // check list items
    expect(item1.classList.contains('disabled')).toBe(false)
    expect(item2.classList.contains('disabled')).toBe(true)
    expect(item3.classList.contains('disabled')).toBe(true)

    // check action buttons
    expect(item1.querySelector('.list-item__actions .v-btn').disabled).toBe(false)
    expect(item2.querySelector('.list-item__actions .v-btn').disabled).toBe(true)
    expect(item3.querySelector('.list-item__actions .v-btn').disabled).toBe(true)

    wrapper.destroy()
  })

  it('displays a NEW \'Annual Report\' task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2019-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent)
      .toContain('(including Address and/or Director Change)')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('File Now')

    wrapper.destroy()
  })

  it('displays a DRAFT \'Annual Report\' task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'DRAFT'
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('DRAFT')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

    wrapper.destroy()
  })

  it('displays a DRAFT \'Address Change\' task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfAddress',
              'ARFilingYear': 2019,
              'status': 'DRAFT'
            },
            'changeOfAddress': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Address Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('DRAFT')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

    wrapper.destroy()
  })

  it('displays a DRAFT \'Director Change\' task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'ARFilingYear': 2019,
              'status': 'DRAFT'
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('DRAFT')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

    wrapper.destroy()
  })

  it('displays a FILING PENDING - PAYMENT INCOMPLETE task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'paymentToken': 12345678
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAYMENT INCOMPLETE')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

    wrapper.destroy()
  })

  it('displays a FILING PENDING - PAYMENT UNSUCCESSFUL task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'ERROR',
              'paymentToken': 12345678
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAYMENT UNSUCCESSFUL')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

    wrapper.destroy()
  })

  it('displays a FILING PENDING - PAID task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'status': 'PAID',
              'paymentToken': 12345678
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAID')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button).toBeNull()

    wrapper.destroy()
  })

  it('displays a PROCESSING message on a filing that is expected to be complete', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'status': 'PENDING',
              'paymentToken': 12345678,
              'filingId': 123
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store,
      vuetify,
      propsData: {
        inProcessFiling: 123
      } })
    const vm = wrapper.vm as any

    // wrapper.setProps({ inProcessFiling: 123 })

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(vm.taskItems[0].id).toEqual(wrapper.props('inProcessFiling'))
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PROCESSING...')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.getAttribute('disabled')).toBe('disabled')

    wrapper.destroy()
  })

  it('does not break if a filing is marked as processing, that is not in the to-do list', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'status': 'PENDING',
              'paymentToken': 12345678,
              'filingId': 123
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    wrapper.setProps({ inProcessFiling: 456 })

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(vm.taskItems[0].id).not.toEqual(wrapper.props('inProcessFiling'))
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAYMENT INCOMPLETE')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

    wrapper.destroy()
  })
})

describe('TodoList - UI - BCOMP', () => {
  beforeAll(() => {
    store.state.entityType = EntityTypes.BCOMP
  })

  it('handles empty data', async () => {
    // init store
    store.state.tasks = []

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(0)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(0)
    expect(wrapper.emitted('todo-count')).toEqual([[0]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).not.toBeNull()
    expect(vm.$el.querySelector('.no-results').textContent).toContain('You don\'t have anything to do yet')

    wrapper.destroy()
  })

  it('displays multiple task items', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2017,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2017-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      },
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2018,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2018-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': false,
        'order': 2
      },
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2019-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': false,
        'order': 3
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(3)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(3)
    expect(wrapper.emitted('todo-count')).toEqual([[3]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    // verify that first task is enabled and other 2 are disabled
    const item1 = vm.$el.querySelectorAll('.todo-item')[0]
    const item2 = vm.$el.querySelectorAll('.todo-item')[1]
    const item3 = vm.$el.querySelectorAll('.todo-item')[2]

    // check list items
    expect(item1.classList.contains('disabled')).toBe(false)
    expect(item2.classList.contains('disabled')).toBe(true)
    expect(item3.classList.contains('disabled')).toBe(true)

    // Check Checkboxes
    expect(item1.querySelector('.todo-list-checkbox')).toBeDefined()
    expect(item2.querySelector('.todo-list-checkbox')).toBeDefined()
    expect(item3.querySelector('.todo-list-checkbox')).toBeDefined()

    // Simulate Checkbox being selected to enable first File Now button
    vm.confirmCheckbox = true

    // check action buttons
    expect(item1.querySelector('.list-item__actions .v-btn').disabled).toBe(false)
    expect(item2.querySelector('.list-item__actions .v-btn').disabled).toBe(true)
    expect(item3.querySelector('.list-item__actions .v-btn').disabled).toBe(true)

    wrapper.destroy()
  })

  it('displays a NEW \'Annual Report\' task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2019-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.bcorps-ar-subtitle').textContent)
      .toContain('Verify your Office Address and Current Directors before filing your Annual Report.')

    // Simulate Checkbox being selected to enable File Now Button
    vm.confirmCheckbox = true

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('File Now')

    wrapper.destroy()
  })

  it('displays a task but `File Now` Btn is disabled when checkbox is unselected', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2019-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.bcorps-ar-subtitle').textContent)
      .toContain('Verify your Office Address and Current Directors before filing your Annual Report.')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(true)
    expect(button.querySelector('.v-btn__content').textContent).toContain('File Now')

    wrapper.destroy()
  })

  it('displays a FILING PENDING - PAYMENT INCOMPLETE task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'paymentToken': 12345678
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAYMENT INCOMPLETE')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

    wrapper.destroy()
  })

  it('displays a FILING PENDING - PAYMENT UNSUCCESSFUL task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'ERROR',
              'paymentToken': 12345678
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAYMENT UNSUCCESSFUL')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

    wrapper.destroy()
  })

  it('displays a FILING PENDING - PAID task', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'status': 'PAID',
              'paymentToken': 12345678
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAID')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button).toBeNull()

    wrapper.destroy()
  })

  it('displays a PROCESSING message on a filing that is expected to be complete', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'status': 'PENDING',
              'paymentToken': 12345678,
              'filingId': 123
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store,
      vuetify,
      propsData: {
        inProcessFiling: 123
      } })
    const vm = wrapper.vm as any

    // wrapper.setProps({ inProcessFiling: 123 })

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(vm.taskItems[0].id).toEqual(wrapper.props('inProcessFiling'))
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PROCESSING...')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.getAttribute('disabled')).toBe('disabled')

    wrapper.destroy()
  })

  it('does not break if a filing is marked as processing, that is not in the to-do list', async () => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'changeOfDirectors',
              'status': 'PENDING',
              'paymentToken': 12345678,
              'filingId': 123
            },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    wrapper.setProps({ inProcessFiling: 456 })

    await flushPromises()

    expect(vm.taskItems.length).toEqual(1)
    expect(vm.$el.querySelectorAll('.todo-item').length).toEqual(1)
    expect(wrapper.emitted('todo-count')).toEqual([[1]])
    expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
    expect(vm.$el.querySelector('.no-results')).toBeNull()

    const item = vm.$el.querySelector('.list-item')
    expect(vm.taskItems[0].id).not.toEqual(wrapper.props('inProcessFiling'))
    expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('FILING PENDING')
    expect(item.querySelector('.list-item__subtitle').textContent).toContain('PAYMENT INCOMPLETE')

    const button = item.querySelector('.list-item__actions .v-btn')
    expect(button.disabled).toBe(false)
    expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

    wrapper.destroy()
  })
})

describe('TodoList - Click Tests', () => {
  const { assign } = window.location

  beforeAll(() => {
    // mock the window.location.assign function
    delete window.location
    window.location = { assign: jest.fn() } as any
    store.state.entityType = EntityTypes.COOP
  })

  afterAll(() => {
    window.location.assign = assign
  })

  it('routes to Annual Report page when \'File Now\' clicked', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2017-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    // create a Local Vue and install router on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    const wrapper = mount(TodoList, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.taskItems.length).toEqual(1)

      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.querySelector('.v-btn__content').textContent).toContain('File Now')

      await button.click()

      // verify that filing status was set
      expect(vm.$store.state.currentFilingStatus).toBe('NEW')

      // verify routing to Annual Report page with id=0
      expect(vm.$route.name).toBe('annual-report')
      expect(vm.$route.params.id).toBe(0)

      wrapper.destroy()
      done()
    })
  })

  it('routes to Annual Report page when \'Resume\' is clicked', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'DRAFT',
              'filingId': 123
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    // create a Local Vue and install router on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    const wrapper = mount(TodoList, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.taskItems.length).toEqual(1)

      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

      await button.click()

      // verify that filing status was set
      expect(vm.$store.state.currentFilingStatus).toBe('DRAFT')

      // verify routing to Annual Report page with id=123
      expect(vm.$route.name).toBe('annual-report')
      expect(vm.$route.params.id).toBe(123)

      wrapper.destroy()
      done()
    })
  })

  it('redirects to Pay URL when \'Resume Payment\' is clicked', done => {
    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', 'auth/')

    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'filingId': 456,
              'paymentToken': 654
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.taskItems.length).toEqual(1)

      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.getAttribute('disabled')).toBeNull()
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

      await button.click()

      // verify redirection
      const payURL = 'auth/makepayment/654/' + encodeURIComponent('cooperatives/dashboard?filing_id=456')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
      done()
    })
  })

  it('redirects to Pay URL when \'Retry Payment\' is clicked', done => {
    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', 'auth/')

    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'ERROR',
              'filingId': 789,
              'paymentToken': 987
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.getAttribute('disabled')).toBeNull()
      expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

      await button.click()

      // verify redirection
      const payURL = 'auth/makepayment/987/' + encodeURIComponent('cooperatives/dashboard?filing_id=789')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
      done()
    })
  })
})

describe('TodoList - Click Tests - BCOMPs', () => {
  const { assign } = window.location

  beforeAll(() => {
    // mock the window.location.assign function
    delete window.location
    window.location = { assign: jest.fn() } as any
    store.state.entityType = EntityTypes.BCOMP
  })

  afterAll(() => {
    window.location.assign = assign
  })

  it('routes to Annual Report page when \'File Now\' clicked', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            },
            'business': {
              'nextAnnualReport': '2017-09-17T00:00:00+00:00'
            }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    // create a Local Vue and install router on it
    const localVue = createLocalVue()
    localVue.use(VueRouter)
    const router = mockRouter.mock()
    const wrapper = mount(TodoList, { localVue, store, router, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.taskItems.length).toEqual(1)

      // verify model state
      expect(vm.confirmCheckbox).toBe(false)

      // verify checkbox content
      const firstTodoItem = vm.$el.querySelectorAll('.todo-item')[0]
      const htmlDivElement = firstTodoItem.querySelector('.bcorps-ar-subtitle .todo-list-checkbox')
      expect(htmlDivElement.textContent)
        .toContain('All information about the Office Addresses and Current Directors is correct.')

      // verify that checkbox is enabled
      const htmlInputElement = htmlDivElement.querySelector('[type="checkbox"]')
      expect(htmlInputElement.disabled).toBe(false)

      // verify File Now button
      const listItem = vm.$el.querySelector('.list-item')
      const fileNowButton = listItem.querySelector('.list-item__actions .v-btn')
      expect(fileNowButton.querySelector('.v-btn__content').textContent).toContain('File Now')
      expect(fileNowButton.disabled).toBe(true)

      // click checkbox to enable File Now button
      await htmlInputElement.click()
      expect(vm.confirmCheckbox).toBe(true)
      expect(fileNowButton.disabled).toBe(false)

      // click File Now button
      await fileNowButton.click()

      // verify that filing status was set
      expect(vm.$store.state.currentFilingStatus).toBe('NEW')

      // verify routing to Annual Report page with id=0
      expect(vm.$route.name).toBe('annual-report')
      expect(vm.$route.params.id).toBe(0)

      wrapper.destroy()
      done()
    })
  })

  it('redirects to Pay URL when \'Resume Payment\' is clicked', done => {
    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', 'auth/')

    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'filingId': 456,
              'paymentToken': 654
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.taskItems.length).toEqual(1)

      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.getAttribute('disabled')).toBeNull()
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

      await button.click()

      // verify redirection
      const payURL = 'auth/makepayment/654/' + encodeURIComponent('cooperatives/dashboard?filing_id=456')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
      done()
    })
  })

  it('redirects to Pay URL when \'Retry Payment\' is clicked', done => {
    // set necessary session variables
    sessionStorage.setItem('BASE_URL', `${process.env.VUE_APP_PATH}/`)
    sessionStorage.setItem('AUTH_URL', 'auth/')

    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'ERROR',
              'filingId': 789,
              'paymentToken': 987
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.getAttribute('disabled')).toBeNull()
      expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

      await button.click()

      // verify redirection
      const payURL = 'auth/makepayment/987/' + encodeURIComponent('cooperatives/dashboard?filing_id=789')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
      done()
    })
  })
})

describe('TodoList - Delete Draft', () => {
  const { assign } = window.location
  let deleteCall

  beforeEach(async () => {
    deleteCall = sinon.stub(axios, 'delete')
  })

  afterEach(() => {
    sinon.restore()
  })

  beforeAll(() => {
    // mock the window.location.assign function
    delete window.location
    window.location = { assign: jest.fn() } as any
  })

  afterAll(() => {
    window.location.assign = assign
  })

  it('shows confirmation popup when \'Delete Draft\' is clicked', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'DRAFT',
              'filingId': 789
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = wrapper.find('#menu-activator')
      await button.trigger('click')
      const button1 = wrapper.find('#btn-delete-draft')
      await button1.trigger('click')
      // verify confirmation popup is showing
      expect(wrapper.vm.$refs.confirm).toBeTruthy()

      await flushPromises()

      done()
    })
  })

  it('calls DELETE API call when user clicks confirmation OK', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'DRAFT',
              'filingId': 789
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = wrapper.find('#menu-activator')
      await button.trigger('click')
      const button1 = wrapper.find('#btn-delete-draft')
      await button1.trigger('click')
      // verify confirmation popup is showing
      expect(vm.$refs.confirm.dialog).toBeTruthy()

      // click the OK button (call the 'yes' callback function)
      await vm.$refs.confirm.onClickYes()

      // confirm that delete API was called
      expect(deleteCall.called).toBeTruthy()

      wrapper.destroy()
      done()
    })
  })

  it('does not call DELETE API call when user clicks confirmation cancel', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'DRAFT',
              'filingId': 789
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = wrapper.find('#menu-activator')
      await button.trigger('click')
      const button1 = wrapper.find('#btn-delete-draft')
      await button1.trigger('click')
      // verify confirmation popup is showing
      expect(vm.$refs.confirm.dialog).toBeTruthy()

      // click the cancel button (call the 'cancel' callback function)
      await vm.$refs.confirm.onClickCancel()

      // confirm that delete API was not called
      expect(deleteCall.called).toBeFalsy()

      wrapper.destroy()
      done()
    })
  })
})

describe('TodoList - Cancel Payment', () => {
  const { assign } = window.location
  let patchCall

  beforeEach(async () => {
    patchCall = sinon.stub(axios, 'patch')
  })

  afterEach(() => {
    sinon.restore()
  })

  beforeAll(() => {
    // mock the window.location.assign function
    delete window.location
    window.location = { assign: jest.fn() } as any
  })

  afterAll(() => {
    window.location.assign = assign
  })

  it('shows confirmation popup when \'Cancel Payment\' is clicked', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'filingId': 789,
              'paymentToken': 123
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = wrapper.find('#pending-item-menu-activator')
      await button.trigger('click')
      const button1 = wrapper.find('#btn-cancel-payment')
      await button1.trigger('click')
      // verify confirmation popup is showing
      expect(wrapper.vm.$refs.confirmCancelPaymentDialog).toBeTruthy()
      done()
    })
  })

  it('calls PATCH endpoint of the API when user clicks confirmation OK', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'filingId': 789,
              'paymentToken': 123
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = wrapper.find('#pending-item-menu-activator')
      await button.trigger('click')
      const button1 = wrapper.find('#btn-cancel-payment')
      await button1.trigger('click')
      // verify confirmation popup is showing
      expect(vm.$refs.confirmCancelPaymentDialog.dialog).toBeTruthy()

      // click the OK button (call the 'yes' callback function)
      await vm.$refs.confirmCancelPaymentDialog.onClickYes()

      // confirm that delete API was called
      expect(patchCall.called).toBeTruthy()

      wrapper.destroy()
      done()
    })
  })

  it('does not call the PATCH endpoint when user clicks confirmation cancel', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'filing': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'PENDING',
              'filingId': 789,
              'paymentToken': 123
            },
            'annualReport': {
              'annualGeneralMeetingDate': '2019-07-15',
              'annualReportDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store, vuetify })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const button = wrapper.find('#pending-item-menu-activator')
      await button.trigger('click')
      const button1 = wrapper.find('#btn-cancel-payment')
      await button1.trigger('click')
      // verify confirmation popup is showing
      expect(vm.$refs.confirmCancelPaymentDialog.dialog).toBeTruthy()

      // click the cancel button (call the 'cancel' callback function)
      await vm.$refs.confirmCancelPaymentDialog.onClickCancel()

      // confirm that delete API was not called
      expect(patchCall.called).toBeFalsy()

      wrapper.destroy()
      done()
    })
  })
})
