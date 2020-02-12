import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { mount } from '@vue/test-utils'
import flushPromises from 'flush-promises'

import store from '@/store/store'
import AgmDate from '@/components/AnnualReport/AGMDate.vue'
import { EntityTypes } from '@/enums'

// NB: test util async issue
// in some cases, the elements are not updated during the test
// the work-around is to first initialize the property we are changing
// suppress update watchers warnings
// ref: https://github.com/vuejs/vue-test-utils/issues/532
Vue.config.silent = true

// get rid of "Download the Vue Devtools extension for a better development experience" console message
Vue.config.devtools = false

// get rid of "You are running Vue in development mode" console message
Vue.config.productionTip = false

Vue.use(Vuetify)
Vue.use(Vuelidate)

const vuetify = new Vuetify({})

describe('AgmDate', () => {
  let wrapper
  let vm

  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.currentDate = '2019-07-15'
    store.state.ARFilingYear = 2019
    store.state.entityType = EntityTypes.COOP
    store.state.lastAnnualReportDate = '2018-07-15'

    wrapper = mount(AgmDate, { store, vuetify })
    vm = wrapper.vm as any

    await flushPromises()
  })

  afterEach(() => {
    wrapper.destroy()
    wrapper = null
  })

  it('initializes the local variables properly', () => {
    // verify local variables
    expect(vm.$data.dateText).toBe('')
    expect(vm.$data.datePicker).toBe('2019-07-15')
    expect(vm.$data.noAgm).toBe(false)

    // verify that checkbox is _not_ rendered (in current year)
    expect(vm.$el.querySelector('#agm-checkbox')).toBeNull()
  })

  it('renders checkbox in past year', () => {
    store.state.ARFilingYear = 2018

    // verify that checkbox is rendered
    expect(vm.$el.querySelector('#agm-checkbox')).not.toBeNull()
  })

  it('sets Min Date properly', () => {
    // verify initial state
    expect(vm.$store.state.ARFilingYear).toBe(2019)

    // first try with a later Last Annual Report date
    store.state.lastAnnualReportDate = '2019-07-15'

    // verify Min Date
    expect(vm.minDate).toBe('2019-07-15')

    // now try with original Last Annual Report Date
    // this also resets the data for other tests
    store.state.lastAnnualReportDate = '2018-07-15'

    // verify Min Date
    expect(vm.minDate).toBe('2019-01-01')
  })

  it('sets Max Date properly', () => {
    // verify initial state
    expect(vm.$store.state.ARFilingYear).toBe(2019)

    // first try with a later Current Date
    store.state.currentDate = '2020-02-07'

    // verify Max Date
    expect(vm.maxDate).toBe('2019-12-31')

    // now try with original Current Date
    // this also resets the data for other tests
    store.state.currentDate = '2019-07-15'

    // verify Max Date
    expect(vm.maxDate).toBe('2019-07-15')
  })

  it('sets AGM Date when date picker is set', () => {
    wrapper.setData({ datePicker: '2019-05-10' })
    vm.onDatePickerChanged('2019-05-10')

    // verify local variables
    expect(vm.$data.dateText).toBe('2019-05-10')
    expect(vm.$data.datePicker).toBe('2019-05-10')
    expect(vm.$data.noAgm).toBe(false)

    // verify emitted AGM Dates
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(1)
    expect(agmDates[0]).toEqual(['2019-05-10'])

    // verify emitted Valids
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([true])
  })

  it('sets No AGM when checkbox is checked', () => {
    wrapper.setData({ noAgm: true })
    vm.onCheckboxChanged(true)

    // verify local variables
    expect(vm.$data.dateText).toBe('')
    expect(vm.$data.datePicker).toBe('2019-07-15')
    expect(vm.$data.noAgm).toBe(true)

    // verify emitted AGM Dates
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(1)
    expect(agmDates[0]).toEqual([''])

    // verify emitted No AGMs
    const noAgms = wrapper.emitted('noAgm')
    expect(noAgms.length).toBe(1)
    expect(noAgms[0]).toEqual([true])

    // verify emitted Valids
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([true])
  })

  it('sets AGM Date when AGM Date prop is set to a date', () => {
    wrapper.setProps({ newAgmDate: '2019-05-10' })

    // verify local variables
    expect(vm.$data.dateText).toBe('2019-05-10')
    expect(vm.$data.datePicker).toBe('2019-05-10')
    expect(vm.$data.noAgm).toBe(false)

    // verify emitted AGM Dates
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(1)
    expect(agmDates[0]).toEqual(['2019-05-10'])

    // verify emitted Valids
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([true])
  })

  it('clears AGM Date when AGM Date prop is set to empty', () => {
    wrapper.setProps({ newAgmDate: '' })

    // verify local variables
    expect(vm.$data.dateText).toBe('')
    expect(vm.$data.datePicker).toBe('2019-07-15')
    expect(vm.$data.noAgm).toBe(false)

    // verify emitted AGM Dates
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(1)
    expect(agmDates[0]).toEqual([''])

    // verify emitted Valids
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([false])
  })

  it('sets No AGM when No AGM prop is set to true', () => {
    wrapper.setProps({ newNoAgm: true })

    // verify local variables
    expect(vm.$data.dateText).toBe('')
    expect(vm.$data.datePicker).toBe('2019-07-15')
    expect(vm.$data.noAgm).toBe(true)

    // verify emitted No AGMs
    const noAgms = wrapper.emitted('noAgm')
    expect(noAgms.length).toBe(1)
    expect(noAgms[0]).toEqual([true])

    // verify emitted Valids
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([true])
  })

  it('displays disabled address change message when allowCOA is false', () => {
    wrapper.setData({ dateText: '2019-07-15' })
    wrapper.setProps({ allowCOA: false })

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent.trim()).toContain(
      'You can not change your Registered Office Addresses in this Annual Report'
    )
  })

  it('displays disabled director change message when allowCOD is false', () => {
    wrapper.setData({ dateText: '2019-07-15' })
    wrapper.setProps({ allowCOD: false })

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent.trim()).toContain(
      'You can not change your Directors in this Annual Report'
    )
  })

  it('displays disabled address + director change message when allowCOA and allowCOD are both false', () => {
    wrapper.setData({ dateText: '2019-07-15' })
    wrapper.setProps({ allowCOA: false, allowCOD: false })

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent.trim()).toContain(
      'You can not change your Registered Office Addresses or Directors in this Annual Report'
    )
  })
})
