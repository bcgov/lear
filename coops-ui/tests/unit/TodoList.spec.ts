import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import VueRouter from 'vue-router'
import { mount, createLocalVue } from '@vue/test-utils'

import mockRouter from './mockRouter'
import store from '@/store/store'
import TodoList from '@/components/Dashboard/TodoList.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('TodoList - UI', () => {
  it('handles empty data', done => {
    // init store
    store.state.tasks = []

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(0)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(0)
      expect(wrapper.emitted('todo-count')).toEqual([[0]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
      expect(vm.$el.querySelector('.no-results')).not.toBeNull()
      expect(vm.$el.querySelector('.no-results').textContent).toContain('You don\'t have anything to do yet')

      wrapper.destroy()
      done()
    })
  })

  it('displays multiple task items', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2017,
              'status': 'NEW'
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
            }
          }
        },
        'enabled': false,
        'order': 3
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(3)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(3)
      expect(wrapper.emitted('todo-count')).toEqual([[3]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      // verify that first task is enabled and other 2 are disabled
      const item1 = vm.$el.querySelectorAll('.todo-list')[0]
      const item2 = vm.$el.querySelectorAll('.todo-list')[1]
      const item3 = vm.$el.querySelectorAll('.todo-list')[2]

      // check list items
      expect(item1.classList.contains('disabled')).toBe(false)
      expect(item2.classList.contains('disabled')).toBe(true)
      expect(item3.classList.contains('disabled')).toBe(true)

      // check action buttons
      expect(item1.querySelector('.list-item__actions .v-btn').disabled).toBe(false)
      expect(item2.querySelector('.list-item__actions .v-btn').disabled).toBe(true)
      expect(item3.querySelector('.list-item__actions .v-btn').disabled).toBe(true)

      wrapper.destroy()
      done()
    })
  })

  it('displays a NEW \'Annual Report\' task', done => {
    // init store
    store.state.tasks = [
      {
        'task': {
          'todo': {
            'header': {
              'name': 'annualReport',
              'ARFilingYear': 2019,
              'status': 'NEW'
            }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(1)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(1)
      expect(wrapper.emitted('todo-count')).toEqual([[1]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[false]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      const item = vm.$el.querySelector('.list-item')
      expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
      expect(item.querySelector('.list-item__subtitle').textContent).toBe('(including Address and/or Director Change)')
      expect(item.querySelector('.list-item__status1')).toBeNull()
      expect(item.querySelector('.list-item__status2')).toBeNull()

      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.disabled).toBe(false)
      expect(button.querySelector('.v-btn__content').textContent).toContain('File Now')

      wrapper.destroy()
      done()
    })
  })

  it('displays a DRAFT \'Annual Report\' task', done => {
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(1)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(1)
      expect(wrapper.emitted('todo-count')).toEqual([[1]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      const item = vm.$el.querySelector('.list-item')
      expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
      expect(item.querySelector('.list-item__subtitle')).toBeNull()
      expect(item.querySelector('.list-item__status1').textContent).toContain('DRAFT')
      expect(item.querySelector('.list-item__status2').textContent).toEqual('')

      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.disabled).toBe(false)
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

      wrapper.destroy()
      done()
    })
  })

  it('displays a DRAFT \'Address Change\' task', done => {
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

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(1)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(1)
      expect(wrapper.emitted('todo-count')).toEqual([[1]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      const item = vm.$el.querySelector('.list-item')
      expect(item.querySelector('.list-item__title').textContent).toEqual('File Address Change')
      expect(item.querySelector('.list-item__subtitle')).toBeNull()
      expect(item.querySelector('.list-item__status1').textContent).toContain('DRAFT')
      expect(item.querySelector('.list-item__status2').textContent).toEqual('')

      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.disabled).toBe(false)
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

      wrapper.destroy()
      done()
    })
  })

  it('displays a DRAFT \'Director Change\' task', done => {
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

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(1)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(1)
      expect(wrapper.emitted('todo-count')).toEqual([[1]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      const item = vm.$el.querySelector('.list-item')
      expect(item.querySelector('.list-item__title').textContent).toEqual('File Director Change')
      expect(item.querySelector('.list-item__subtitle')).toBeNull()
      expect(item.querySelector('.list-item__status1').textContent).toContain('DRAFT')
      expect(item.querySelector('.list-item__status2').textContent).toEqual('')

      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.disabled).toBe(false)
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume')

      wrapper.destroy()
      done()
    })
  })

  it('displays a FILING PENDING - PAYMENT INCOMPLETE task', done => {
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(1)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(1)
      expect(wrapper.emitted('todo-count')).toEqual([[1]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      const item = vm.$el.querySelector('.list-item')
      expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
      expect(item.querySelector('.list-item__subtitle')).toBeNull()
      expect(item.querySelector('.list-item__status1').textContent).toContain('FILING PENDING')
      expect(item.querySelector('.list-item__status2').textContent).toContain('PAYMENT INCOMPLETE')

      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.disabled).toBe(false)
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

      wrapper.destroy()
      done()
    })
  })

  it('displays a FILING PENDING - PAYMENT UNSUCCESSFUL task', done => {
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.taskItems.length).toEqual(1)
      expect(vm.$el.querySelectorAll('.todo-list').length).toEqual(1)
      expect(wrapper.emitted('todo-count')).toEqual([[1]])
      expect(wrapper.emitted('has-blocker-filing')).toEqual([[true]])
      expect(vm.$el.querySelector('.no-results')).toBeNull()

      const item = vm.$el.querySelector('.list-item')
      expect(item.querySelector('.list-item__title').textContent).toEqual('File 2019 Annual Report')
      expect(item.querySelector('.list-item__subtitle')).toBeNull()
      expect(item.querySelector('.list-item__status1').textContent).toContain('FILING PENDING')
      expect(item.querySelector('.list-item__status2').textContent).toContain('PAYMENT UNSUCCESSFUL')

      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.disabled).toBe(false)
      expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

      wrapper.destroy()
      done()
    })
  })

  it('disables Resume Payment button if user has \'staff\' role', done => {
    // init store
    store.state.keycloakRoles = ['staff']
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.isRoleStaff).toBe(true)

      // sanity checks
      expect(vm.taskItems.length).toEqual(1)
      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

      // verify that doResumePayment() does nothing
      expect(await vm.doResumePayment()).toBe(false)

      // NB: cannot verify v-tooltip text as Vue puts it in a div outside this component

      store.state.keycloakRoles = [] // cleanup

      wrapper.destroy()
      done()
    })
  })

  it('disables Retry Payment button if user has \'staff\' role', done => {
    // init store
    store.state.keycloakRoles = ['staff']
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.isRoleStaff).toBe(true)

      // sanity checks
      expect(vm.taskItems.length).toEqual(1)
      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

      // verify that doResumePayment() does nothing
      expect(await vm.doResumePayment()).toBe(false)

      // NB: cannot verify v-tooltip text as Vue puts it in a div outside this component

      store.state.keycloakRoles = [] // cleanup

      wrapper.destroy()
      done()
    })
  })
})

describe('TodoList - Click Tests', () => {
  const { assign } = window.location

  beforeAll(() => {
    // mock the window.location.assign function
    delete window.location
    window.location = { assign: jest.fn() } as any
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
    const wrapper = mount(TodoList, { localVue, store, router })
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
              'annualGeneralMeetingDate': '2019-07-15'
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
    const wrapper = mount(TodoList, { localVue, store, router })
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      expect(vm.taskItems.length).toEqual(1)

      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.getAttribute('disabled')).toBeNull()
      expect(button.querySelector('.v-btn__content').textContent).toContain('Resume Payment')

      await button.click()

      // verify redirection
      const payURL = '/makepayment/654/' + encodeURIComponent('/dashboard?filing_id=456')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
      done()
    })
  })

  it('redirects to Pay URL when \'Retry Payment\' is clicked', done => {
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
              'annualGeneralMeetingDate': '2019-07-15'
            },
            'changeOfAddress': { },
            'changeOfDirectors': { }
          }
        },
        'enabled': true,
        'order': 1
      }
    ]

    const wrapper = mount(TodoList, { store })
    const vm = wrapper.vm as any

    Vue.nextTick(async () => {
      const item = vm.$el.querySelector('.list-item')
      const button = item.querySelector('.list-item__actions .v-btn')
      expect(button.getAttribute('disabled')).toBeNull()
      expect(button.querySelector('.v-btn__content').textContent).toContain('Retry Payment')

      await button.click()

      // verify redirection
      const payURL = '/makepayment/987/' + encodeURIComponent('/dashboard?filing_id=789')
      expect(window.location.assign).toHaveBeenCalledWith(payURL)

      wrapper.destroy()
      done()
    })
  })
})
