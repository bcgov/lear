import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { shallowMount } from '@vue/test-utils'

import store from '@/store/store'
import FilingHistoryList from '@/components/Dashboard/FilingHistoryList.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('FilingHistoryList', () => {
  it('handles empty data', done => {
    const $route = { query: { 'filingId': null } }

    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.filings = []

    const wrapper = shallowMount(FilingHistoryList, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.filedItems.length).toEqual(0)
      expect(vm.$el.querySelectorAll('.filing-history-list').length).toEqual(0)
      expect(wrapper.emitted('filed-count')).toEqual([[0]])
      expect(vm.panel).toBeNull() // no row is expanded
      expect(vm.$el.querySelector('.no-results')).not.toBeNull()
      expect(vm.$el.querySelector('.no-results').textContent).toContain('You have no filing history')
      wrapper.destroy()
      done()
    })
  })

  it('displays the Filed Items', done => {
    const $route = { query: { 'filingId': null } }

    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.filings = [
      {
        'filing': {
          'header': {
            'name': 'annualReport',
            'date': '2019-01-02',
            'paymentToken': 123,
            'certifiedBy': 'Full Name 1',
            'filingId': 321
          },
          'annualReport': {
            'annualGeneralMeetingDate': '2019-12-31'
          }
        }
      },
      {
        'filing': {
          'header': {
            'name': 'changeOfDirectors',
            'date': '2019-03-04',
            'paymentToken': 456,
            'certifiedBy': 'Full Name 2',
            'filingId': 654
          },
          'changeOfDirectors': {
          }
        }
      },
      {
        'filing': {
          'header': {
            'name': 'changeOfAddress',
            'date': '2019-05-06',
            'paymentToken': 789,
            'certifiedBy': 'Full Name 3',
            'filingId': 987
          },
          'changeOfAddress': {
          }
        }
      }
    ]

    const wrapper = shallowMount(FilingHistoryList, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.filedItems.length).toEqual(3)
      expect(vm.$el.querySelectorAll('.filing-history-list').length).toEqual(3)
      expect(wrapper.emitted('filed-count')).toEqual([[3]])
      expect(vm.panel).toBeNull() // no row is expanded
      expect(vm.$el.querySelector('.no-results')).toBeNull()
      wrapper.destroy()
      done()
    })
  })

  it('expands the specified filing ID', done => {
    const $route = { query: { 'filing_id': '654' } }

    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.filings = [
      {
        'filing': {
          'header': {
            'name': 'annualReport',
            'date': '2019-01-02',
            'paymentToken': 123,
            'certifiedBy': 'Full Name 1',
            'filingId': 321
          },
          'annualReport': {
            'annualGeneralMeetingDate': '2019-12-31'
          }
        }
      },
      {
        'filing': {
          'header': {
            'name': 'changeOfDirectors',
            'date': '2019-03-04',
            'paymentToken': 456,
            'certifiedBy': 'Full Name 2',
            'filingId': 654
          },
          'changeOfDirectors': {
          }
        }
      },
      {
        'filing': {
          'header': {
            'name': 'changeOfAddress',
            'date': '2019-05-06',
            'paymentToken': 789,
            'certifiedBy': 'Full Name 3',
            'filingId': 987
          },
          'changeOfAddress': {
          }
        }
      }
    ]

    const wrapper = shallowMount(FilingHistoryList, { store, mocks: { $route } })
    const vm = wrapper.vm as any

    Vue.nextTick(() => {
      expect(vm.filedItems.length).toEqual(3)
      expect(vm.$el.querySelectorAll('.filing-history-list').length).toEqual(3)
      expect(wrapper.emitted('filed-count')).toEqual([[3]])
      expect(vm.panel).toEqual(1) // second row is expanded
      expect(vm.$el.querySelector('.no-results')).toBeNull()
      wrapper.destroy()
      done()
    })
  })
})
