/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { shallowMount } from '@vue/test-utils'

import store from '@/store/store'
import SaveErrorDialog from '@/components/AnnualReport/SaveErrorDialog.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('SaveErrorDialogue - Part 1 - Displays Error/Warning messages', () => {
  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.ARFilingYear = 2017
    store.state.currentFilingStatus = 'NEW'
  })

  it('Displays errors', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(SaveErrorDialog,
      {
        store,
        mocks: {
          $route
        },
        propsData: {
          dialogue: true,
          errors: [
            {
              'error': 'error msg',
              'path': 'path/path'
            }
          ],
          warnings: []
        }
      })
    const vm: any = wrapper.vm
    expect(vm.errors[0].error).toBe('error msg')
    expect(wrapper.find('#error-dialogue-title').text()).toBe('Unable to Save Filing')
    expect(wrapper.find('#dialogue-text').text()).toContain('error msg')
    expect(wrapper.find('#okay-btn')).toBeDefined()
    wrapper.destroy()
  })

  it('Displays warnings', () => {
    const $route = { params: { id: '0' } } // new filing id
    const wrapper = shallowMount(SaveErrorDialog,
      {
        store,
        mocks: {
          $route
        },
        propsData: {
          dialogue: true,
          errors: [],
          warnings: [
            {
              'warning': 'warning msg',
              'path': 'path/path'
            }
          ]
        }
      })
    const vm: any = wrapper.vm
    expect(vm.warnings[0].warning).toBe('warning msg')
    expect(wrapper.find('#warning-dialogue-title').text()).toBe('Filing Saved with Warnings')
    expect(wrapper.find('#dialogue-text').text()).toContain('warning msg')
    expect(wrapper.find('#okay-btn')).toBeDefined()
    wrapper.destroy()
  })
})
