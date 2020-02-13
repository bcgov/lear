import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import { shallowMount } from '@vue/test-utils'
import ArDate from '@/components/AnnualReport/BCorp/ARDate.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AnnualReport - Part 1 - UI', () => {
  beforeEach(() => {
    // init store
    store.state.currentDate = '2019/07/15'
    store.state.nextARDate = '2020-09-18T23:15:53.785045+00:00'
  })

  it('initializes the store variables properly', () => {
    const wrapper = shallowMount(ArDate, { store })
    const vm: any = wrapper.vm

    expect(vm.$store.state.currentDate).toEqual('2019/07/15')
    expect(vm.$store.state.nextARDate).toEqual('2020-09-18T23:15:53.785045+00:00')

    wrapper.destroy()
  })

  it('succeeds when the Annual report date outputs are correct', () => {
    const wrapper = shallowMount(ArDate, { store })
    const vm: any = wrapper.vm
    const regex = / (?!.* )/
    const today = new Date().toDateString().split(' ').slice(1).join(' ').replace(regex, ', ')

    expect(vm.$el.querySelector('.ar-date').textContent).toContain('Sep 18, 2020')
    expect(vm.$el.querySelector('.file-date').textContent).toContain(`Today (${today})`)

    wrapper.destroy()
  })
})
