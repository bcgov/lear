/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import { shallowMount } from '@vue/test-utils'
import SaveErrorDialog from '@/components/AnnualReport/SaveErrorDialog.vue'

Vue.use(Vuetify)

let vuetify = new Vuetify({})

describe('SaveErrorDialogue - Part 1 - Displays Error/Warning messages', () => {
  it('displays generic message', () => {
    const wrapper = shallowMount(SaveErrorDialog,
      {
        propsData: {
          filing: 'FILING',
          dialog: true
        },
        vuetify
      })
    const vm: any = wrapper.vm

    expect(wrapper.find('#error-dialogue-title').text()).toBe('Unable to save FILING')
    expect(wrapper.find('#dialogue-text').text())
      .toContain('We were unable to save your FILING. You can continue to try to save this')
    expect(wrapper.find('#exit-btn')).toBeDefined()
    expect(wrapper.find('#retry-btn')).toBeDefined()

    wrapper.destroy()
  })

  it('displays errors', () => {
    const wrapper = shallowMount(SaveErrorDialog,
      {
        propsData: {
          dialog: true,
          errors: [
            {
              error: 'error msg',
              path: 'path/path'
            }
          ]
        },
        vuetify
      })
    const vm: any = wrapper.vm

    expect(vm.errors[0].error).toBe('error msg')
    expect(wrapper.find('#error-dialogue-title').text()).toBe('Unable to save Filing')
    expect(wrapper.find('#dialogue-text').text())
      .toContain('We were unable to save your Filing due to the following errors:')
    expect(wrapper.find('#dialogue-text').text()).toContain('error msg')
    expect(wrapper.find('#okay-btn')).toBeDefined()

    wrapper.destroy()
  })

  it('displays warnings', () => {
    const wrapper = shallowMount(SaveErrorDialog,
      {
        propsData: {
          dialog: true,
          warnings: [
            {
              warning: 'warning msg',
              path: 'path/path'
            }
          ]
        },
        vuetify
      })
    const vm: any = wrapper.vm

    expect(vm.warnings[0].warning).toBe('warning msg')
    expect(wrapper.find('#warning-dialogue-title').text()).toBe('Filing saved with warnings')
    expect(wrapper.find('#dialogue-text').text()).toContain('Please note the following warnings:')
    expect(wrapper.find('#dialogue-text').text()).toContain('warning msg')
    expect(wrapper.find('#okay-btn')).toBeDefined()

    wrapper.destroy()
  })
})
