import Vue from 'vue'
import Vuetify from 'vuetify'
import { mount } from '@vue/test-utils'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'

Vue.use(Vuetify)
// suppress "avoid mutating a prop directly" warnings
// https://vue-test-utils.vuejs.org/api/config.html#silent
Vue.config.silent = true

let vuetify = new Vuetify({})

describe('StaffPayment', () => {
  it('initializes correctly with no prop', async () => {
    const wrapper = mount(StaffPayment,
      {
        propsData: { value: null },
        vuetify
      })

    // check that:
    // 1. value is initially null
    // 2. component is initially invalid
    expect(wrapper.emitted('update:value')).toEqual([[null]])
    expect(wrapper.emitted('valid')).toEqual([[false]])

    wrapper.destroy()
  })

  it('initializes correctly with prop', async () => {
    const wrapper = mount(StaffPayment,
      {
        propsData: { value: '123456789' },
        vuetify
      })

    // check that:
    // 1. value is initially set
    // 2. component is initially valid
    expect(wrapper.emitted('update:value')).toEqual([['123456789']])
    setTimeout(() => {
      expect(wrapper.emitted('valid')).toEqual([[true]])
    }, 100)

    wrapper.destroy()
  })

  it('becomes valid when prop becomes valid', async () => {
    const wrapper = mount(StaffPayment,
      {
        propsData: { value: null },
        vuetify
      })

    wrapper.setProps({ value: '123456789' })

    // check that:
    // 1. value was initially null
    // 2. value became set
    // 3. component was initially invalid
    // 4. component became valid
    expect(wrapper.emitted('update:value')).toEqual([[null], ['123456789']])
    setTimeout(() => {
      expect(wrapper.emitted('valid')).toEqual([[false], [true]])
    }, 100)
    wrapper.destroy()
  })

  it('becomes invalid when prop becomes invalid', async () => {
    const wrapper = mount(StaffPayment,
      {
        propsData: { value: '123456789' },
        vuetify
      })

    wrapper.setProps({ value: null })

    // NB: can't check error message because Vuetify renders it outside this component

    // check that:
    // 1. value was initially set
    // 2. value became null
    // 3. component was initially valid
    // 4. component became invalid
    expect(wrapper.emitted('update:value')).toEqual([['123456789'], [null]])
    setTimeout(() => {
      expect(wrapper.emitted('valid')).toEqual([[true], [false]])
    }, 100)

    wrapper.destroy()
  })

  it('becomes valid when input becomes valid', async () => {
    const wrapper = mount(StaffPayment,
      {
        propsData: { value: null },
        vuetify
      })

    wrapper.setData({ routingSlipNumber: '123456789' })

    // check that:
    // 1. value was initially null
    // 2. value became set
    // 3. component was initially invalid
    // 4. component became valid
    expect(wrapper.emitted('update:value')).toEqual([[null], ['123456789']])
    setTimeout(() => {
      expect(wrapper.emitted('valid')).toEqual([[false], [true]])
    }, 100)
    wrapper.destroy()
  })

  it('becomes invalid when input becomes invalid', async () => {
    const wrapper = mount(StaffPayment,
      {
        propsData: { value: '123456789' },
        vuetify
      })

    wrapper.setData({ routingSlipNumber: null })

    // NB: can't check error message because Vuetify renders it outside this component

    // check that:
    // 1. value was initially set
    // 2. value became null
    // 3. component was initially valid
    // 4. component became invalid
    expect(wrapper.emitted('update:value')).toEqual([['123456789'], [null]])
    setTimeout(() => {
      expect(wrapper.emitted('valid')).toEqual([[true], [false]])
    }, 100)

    wrapper.destroy()
  })
})
