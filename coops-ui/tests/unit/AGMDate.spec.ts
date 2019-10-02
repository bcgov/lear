import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { mount } from '@vue/test-utils'
import flushPromises from 'flush-promises'

import store from '@/store/store'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'

// NB: test util async issue
// in some cases, the elements are not updated during the test
// the work-around is to first initialize the property we are changing

Vue.use(Vuetify)
Vue.use(Vuelidate)

// get rid of "Download the Vue Devtools extension for a better development experience" console message
Vue.config.devtools = false

// get rid of "You are running Vue in development mod" console message
Vue.config.productionTip = false

describe('AGMDate', () => {
  let wrapper
  let vm

  beforeEach(async () => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    wrapper = mount(AGMDate, { store })
    vm = wrapper.vm as any

    await flushPromises()
  })

  afterEach(() => {
    wrapper.destroy()
    wrapper = null
  })

  it('initializes the local variables properly', () => {
    // verify local variables
    expect(vm.$data.date).toBe('2019-01-01')
    expect(vm.$data.dateFormatted).toBe('2019/01/01')
    expect(vm.$data.didNotHoldAgm).toBe(false)

    // verify emitted AGM Dates
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(1)
    expect(agmDates[0]).toEqual(['2019-01-01'])

    // verify emitted Valids
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([true])

    // verify emitted No AGMs
    expect(wrapper.emitted('noAGM')).toBeUndefined()

    // verify that checkbox is not rendered (in current year)
    expect(vm.$el.querySelector('#agm-checkbox')).toBeNull()

    // verify that there are no validation errors
    expect(vm.$el.querySelector('.validationErrorInfo').textContent).toBe('')
  })

  it('renders checkbox in past year', () => {
    store.state.ARFilingYear = 2018

    // verify that checkbox is rendered
    expect(vm.$el.querySelector('#agm-checkbox')).not.toBeNull()
  })

  it('loads variables properly when initial AGM Date is set', () => {
    wrapper.setProps({ initialAgmDate: '2019-05-10' })

    // verify local variables
    expect(vm.$data.date).toBe('2019-05-10')
    expect(vm.$data.dateFormatted).toBe('2019/05/10')
    expect(vm.$data.didNotHoldAgm).toBe(false)

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from prop update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual(['2019-05-10'])

    // verify emitted Valids
    // first emit is from init
    // second emit is from prop update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([true])

    // verify emitted No AGMs
    expect(wrapper.emitted('noAGM')).toBeUndefined()
  })

  it('loads variables properly when initial AGM Date is cleared', () => {
    wrapper.setProps({ initialAgmDate: null })

    // verify local variables
    expect(vm.$data.date).toBe('')
    expect(vm.$data.dateFormatted).toBeNull()
    expect(vm.$data.didNotHoldAgm).toBe(true)

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from prop update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from 'date' watcher
    // third emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(3)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([true])
    expect(valids[2]).toEqual([true])

    // verify emitted No AGMs
    const noAGMs = wrapper.emitted('noAGM')
    expect(noAGMs.length).toBe(1)
    expect(noAGMs[0]).toEqual([true])
  })

  it('sets Min Date properly based on global properties', () => {
    // verify initial state
    expect(vm.$store.state.ARFilingYear).toBe(2019)
    expect(vm.$store.state.filings).toEqual([])
    expect(vm.$store.state.lastPreLoadFilingDate).toBeNull()

    // verify default Min Date
    expect(vm.minDate).toBe('2019-01-01')

    // set Last Filing Date and verify new Min Date
    store.state.filings = [
      { filing: { header: { date: '2019-02-01' } } },
      { filing: { header: { date: '2019-03-01' } } }
    ]
    expect(vm.minDate).toBe('2019-03-01')

    // set Last Pre-Load Filing Date and verify new date
    store.state.lastPreLoadFilingDate = '2019-04-01'
    expect(vm.minDate).toBe('2019-04-01')

    // cleanup
    store.state.filings = []
    store.state.lastPreLoadFilingDate = null
  })

  it('sets date picker when text field is set', () => {
    wrapper.setData({ dateFormatted: '2019/05/10' })

    // verify local variables
    expect(vm.$data.date).toBe('2019-05-10')
    expect(vm.$data.didNotHoldAgm).toBe(false)

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual(['2019-05-10'])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([true])

    // verify emitted No AGMs
    expect(wrapper.emitted('noAGM')).toBeUndefined()
  })

  it('sets text field when date picker is set', () => {
    wrapper.setData({ date: '2019-05-10' })

    // verify local variables
    expect(vm.$data.dateFormatted).toBe('2019/05/10')
    expect(vm.$data.didNotHoldAgm).toBe(false)

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from date picker update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual(['2019-05-10'])

    // verify emitted Valids
    // first emit is from init
    // second emit is from date picker update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([true])

    // verify emitted No AGMs
    expect(wrapper.emitted('noAGM')).toBeUndefined()
  })

  it('invalidates the component when date is empty', () => {
    wrapper.setData({ dateFormatted: '' })

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation messages
    expect(vm.$el.querySelector('.v-messages').textContent)
      .toContain('An Annual General Meeting date is required.')
  })

  it('invalidates the component when date has invalid length', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/06/1' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Date must be in format YYYY/MM/DD.')
  })

  it('invalidates the component when date has invalid first slash', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019.06/15' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Date must be in format YYYY/MM/DD.')
  })

  it('invalidates the component when date has invalid second slash', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/06.15' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Date must be in format YYYY/MM/DD.')
  })

  it('invalidates the component when date has invalid third slash', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/06///' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Date must be in format YYYY/MM/DD.')
  })

  it('invalidates the component when entered year is invalid', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2020/01/01' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a year within 2019.')
  })

  it('invalidates the component when entered month is an invalid number', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/13/01' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a month between 2019/01/01 and 2019/07/15.')
  })

  it('invalidates the component when entered month is before Min Date', () => {
    store.state.lastPreLoadFilingDate = '2019-03-01' // to set new Min Date

    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/02/01' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a month between 2019/03/01 and 2019/07/15.')

    // cleanup
    store.state.lastPreLoadFilingDate = null
  })

  it('invalidates the component when entered month is after Max Date', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/08/15' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a month between 2019/01/01 and 2019/07/15.')
  })

  it('invalidates the component when entered day is an invalid number', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/01/32' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a day between 2019/01/01 and 2019/07/15.')
  })

  it('invalidates the component when entered day is invalid in non leap year', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/02/29' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a day between 2019/01/01 and 2019/07/15.')
  })

  it('validates the component when entered day is valid in leap year', () => {
    store.state.ARFilingYear = 2020 // leap year

    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2020/02/29' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from first text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(3)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])
    expect(agmDates[2]).toEqual(['2020-02-29'])

    // verify emitted Valids
    // first emit is from init
    // second emit is from first text field update
    // third emit is from second text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(3)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])
    expect(valids[2]).toEqual([true])

    // verify that there are no validation errors
    expect(vm.$el.querySelector('.validationErrorInfo').textContent).toBe('')

    // cleanup
    store.state.ARFilingYear = 2019
  })

  it('invalidates the component when entered day is before Min Date', () => {
    store.state.lastPreLoadFilingDate = '2019-04-15' // to set new Min Date

    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/04/01' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a day between 2019/04/15 and 2019/07/15.')

    // cleanup
    store.state.lastPreLoadFilingDate = null
  })

  it('invalidates the component when entered day is after Max Date', () => {
    wrapper.setData({ dateFormatted: '' }) // work-around for test util async issue
    wrapper.setData({ dateFormatted: '2019/07/20' })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from text field update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([false])

    // verify validation error
    expect(vm.$el.querySelector('.validationErrorInfo').textContent)
      .toContain('Please enter a day between 2019/01/01 and 2019/07/15.')
  })

  it('validates the component when Did Not Hold AGM is checked', () => {
    wrapper.setData({ didNotHoldAgm: true })

    // verify emitted AGM Dates
    // first emit is from init
    // second emit is from checkbox update
    const agmDates = wrapper.emitted('agmDate')
    expect(agmDates.length).toBe(2)
    expect(agmDates[0]).toEqual(['2019-01-01'])
    expect(agmDates[1]).toEqual([null])

    // verify emitted Valids
    // first emit is from init
    // second emit is from checkbox update
    // third emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(3)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([true])
    expect(valids[2]).toEqual([true])

    // verify emitted No AGMs
    // first emit is from init
    // second emit is from text field update
    const noAGMs = wrapper.emitted('noAGM')
    expect(noAGMs.length).toBe(1)
    expect(noAGMs[0]).toEqual([true])

    // verify that there are no validation errors
    expect(vm.$el.querySelector('.validationErrorInfo')).toBeNull()
  })

  it('Displays disabled address change message when allowCOA is false', () => {
    wrapper.setProps({ allowCOA: false })
    expect(vm.$el.querySelector('.validationErrorInfo').textContent.trim()).toContain(
      'You can not change your Registered Office Addresses in this Annual Report')
  })
  it('Displays disabled director change message when allowCOD is false', () => {
    wrapper.setProps({ allowCOD: false })
    expect(vm.$el.querySelector('.validationErrorInfo').textContent.trim()).toContain(
      'You can not change your Directors in this Annual Report')
  })
  it('Displays disabled address + director change message when allowCOA and allowCOD are both false', () => {
    wrapper.setProps({ allowCOA: false, allowCOD: false })
    expect(vm.$el.querySelector('.validationErrorInfo').textContent.trim()).toContain(
      'You can not change your Registered Office Addresses or Directors in this Annual Report')
  })
})
