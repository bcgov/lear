/* eslint promise/param-names: 0, prefer-promise-reject-errors: 0 */
import Vue from 'vue'
import Vuetify from 'vuetify'
import { shallowMount } from '@vue/test-utils'
import store from '@/store/store'
import { SaveErrorDialog } from '@/components/dialogs'

Vue.use(Vuetify)

let vuetify = new Vuetify({})

describe('SaveErrorDialog - Part 1 - Displays Error/Warning messages', () => {
  it('displays generic message for normal users', () => {
    const wrapper = shallowMount(SaveErrorDialog,
      {
        propsData: {
          filing: 'FILING',
          dialog: true
        },
        store,
        vuetify
      })
    const vm: any = wrapper.vm

    expect(wrapper.find('#dialog-title').text()).toBe('Unable to save FILING')
    expect(wrapper.find('#dialog-text').text())
      .toContain('We were unable to save your FILING. You can continue to try to save this')
    expect(wrapper.find('#dialog-text').text()).toContain('If you need help, please contact us')
    expect(wrapper.find('#dialog-exit-button')).toBeDefined()
    expect(wrapper.find('#dialog-retry-button')).toBeDefined()

    wrapper.destroy()
  })

  it('displays generic message for staff', () => {
    // init store
    store.state.keycloakRoles.push('staff')
    const wrapper = shallowMount(SaveErrorDialog,
      {
        propsData: {
          filing: 'FILING',
          dialog: true
        },
        store,
        vuetify
      })
    const vm: any = wrapper.vm

    expect(wrapper.find('#dialog-title').text()).toBe('Unable to save FILING')
    expect(wrapper.find('#dialog-text').text())
      .toContain('We were unable to save your FILING. You can continue to try to save this')
    expect(wrapper.find('#dialog-text').text()).not.toContain('If you need help, please contact us')
    expect(wrapper.find('#dialog-exit-button')).toBeDefined()
    expect(wrapper.find('#dialog-retry-button')).toBeDefined()

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
        store,
        vuetify
      })
    const vm: any = wrapper.vm

    expect(vm.errors[0].error).toBe('error msg')
    expect(wrapper.find('#dialog-title').text()).toBe('Unable to save Filing')
    expect(wrapper.find('#dialog-text').text())
      .toContain('We were unable to save your Filing due to the following errors:')
    expect(wrapper.find('#dialog-text').text()).toContain('error msg')
    expect(wrapper.find('#dialog-ok-button')).toBeDefined()

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
        store,
        vuetify
      })
    const vm: any = wrapper.vm

    expect(vm.warnings[0].warning).toBe('warning msg')
    expect(wrapper.find('#dialog-title').text()).toBe('Filing saved with warnings')
    expect(wrapper.find('#dialog-text').text()).toContain('Please note the following warnings:')
    expect(wrapper.find('#dialog-text').text()).toContain('warning msg')
    expect(wrapper.find('#dialog-ok-button')).toBeDefined()

    wrapper.destroy()
  })
})
