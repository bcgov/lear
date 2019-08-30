import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { mount } from '@vue/test-utils'
import flushPromises from 'flush-promises'

import store from '@/store/store'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AGMDate', () => {
  let wrapper
  let vm

  beforeEach(async () => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019
    // store.state.lastFilingDate = '2019/01/01' // TODO: test this
    // store.state.lastPreLoadFilingDate = '2019/01/01' // TODO: test this

    wrapper = mount(AGMDate, { store })
    vm = wrapper.vm as any

    await flushPromises()
  })

  afterEach(() => {
    wrapper.destroy()
  })

  // TODO - set initialAgmDate to various values and verify:
  //   agmDate
  //   noAGM
  //   valid

  it('initializes the local variables properly', () => {
    expect(vm.date).toBe('2019-01-01')
    expect(vm.dateFormatted).toBe('2019/01/01')
    expect(vm.didNotHoldAGM).toBe(false)
    expect(wrapper.emitted('valid')[0]).toEqual([true])

    // verify checkbox
    expect(vm.$el.querySelector('#agm-checkbox')).toBeDefined()
  })

  it('sets date picker when text field is set', async () => {
    vm.dateFormatted = '2019/05/10'
    await flushPromises()

    // check local variable
    expect(vm.$data.date).toBe('2019-05-10')

    // check global variable
    expect(vm.agmDate).toBe('2019-05-10')
  })

  it('sets text field when date picker is set', async () => {
    vm.date = '2019-05-10'
    await flushPromises()

    // check local variable
    expect(vm.$data.dateFormatted).toBe('2019/05/10')

    // check global variable
    expect(vm.agmDate).toBe('2019-05-10')
  })

  it('doesn\'t render checkbox in current year', async () => {
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019
    await flushPromises()

    expect(vm.$el.querySelector('#agm-checkbox')).toBeNull()
  })

  it('invalidates the component when date is empty', async () => {
    const emits = wrapper.emitted('valid')

    // check initial state
    expect(emits.length).toBe(1)
    expect(emits[0]).toEqual([true])

    // empty
    vm.$data.dateFormatted = ''
    await flushPromises()

    expect(emits.length).toBe(2)
    expect(emits[1]).toEqual([false])
    expect(vm.$el.querySelector('.v-messages').textContent)
      .toContain('An Annual General Meeting date is required.')
  })

  it('invalidates the component when entered format is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')
    const emits = wrapper.emitted('valid')

    // check initial state
    expect(emits.length).toBe(1)
    expect(emits[0]).toEqual([true])
    expect(validationErrorInfo.textContent).toBe('')

    // invalid length
    vm.$data.dateFormatted = '2019/06/1'
    await flushPromises()

    expect(emits.length).toBe(2)
    expect(emits[1]).toEqual([false])
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

    // invalid first slash
    vm.$data.dateFormatted = '2019.06/15'
    await flushPromises()

    // NB: no new emit so check properties
    expect(emits.length).toBe(2)
    expect(Boolean(vm.didNotHoldAGM || vm.agmDate)).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

    // invalid second slash
    vm.$data.dateFormatted = '2019/06.15'
    await flushPromises()

    // NB: no new emit so check properties
    expect(emits.length).toBe(2)
    expect(Boolean(vm.didNotHoldAGM || vm.agmDate)).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

    // invalid third slash
    vm.$data.dateFormatted = '2019/06///'
    await flushPromises()

    // NB: no new emit so check properties
    expect(emits.length).toBe(2)
    expect(Boolean(vm.didNotHoldAGM || vm.agmDate)).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')
  })

  it('invalidates the component when entered year is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')
    const emits = wrapper.emitted('valid')

    // check initial state
    expect(emits.length).toBe(1)
    expect(emits[0]).toEqual([true])
    expect(validationErrorInfo.textContent).toBe('')

    // invalid year
    vm.$data.dateFormatted = '2020/01/01'
    await flushPromises()

    expect(emits.length).toBe(2)
    expect(emits[1]).toEqual([false])
    expect(validationErrorInfo.textContent).toContain('Please enter a date within 2019.')
  })

  it('invalidates the component when entered month is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')
    const emits = wrapper.emitted('valid')

    // check initial state
    expect(emits.length).toBe(1)
    expect(emits[0]).toEqual([true])
    expect(validationErrorInfo.textContent).toBe('')

    // invalid month number
    vm.$data.dateFormatted = '2019/13/01'
    await flushPromises()

    expect(emits.length).toBe(2)
    expect(emits[1]).toEqual([false])
    expect(validationErrorInfo.textContent).toContain('Please enter a valid month in the past.')

    // invalid future month
    vm.$data.dateFormatted = '2019/08/15'
    await flushPromises()

    // NB: no new emit so check properties
    expect(emits.length).toBe(2)
    expect(Boolean(vm.didNotHoldAGM || vm.agmDate)).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a valid month in the past.')
  })

  it('invalidates the component when entered day is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')
    const emits = wrapper.emitted('valid')

    // check initial state (date was initialized to 2019/01/01)
    expect(emits.length).toBe(1)
    expect(emits[0]).toEqual([true])
    expect(validationErrorInfo.textContent).toBe('')

    // invalid day number (Feb 29 on non leap year)
    vm.$data.dateFormatted = '2019/02/29'
    await flushPromises()

    expect(emits.length).toBe(2)
    expect(emits[1]).toEqual([false])
    expect(validationErrorInfo.textContent).toContain('Please enter a valid day in the past.')

    // invalid day number (future day)
    vm.$data.dateFormatted = '2019/07/20'
    await flushPromises()

    // NB: no new emit so check properties
    expect(emits.length).toBe(2)
    expect(Boolean(vm.didNotHoldAGM || vm.agmDate)).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a valid day in the past.')

    // valid day number (day in the past, this year, with day number > current day number)
    vm.$data.dateFormatted = '2019/06/20'
    await flushPromises()

    expect(emits.length).toBe(3)
    expect(emits[2]).toEqual([true])
    expect(validationErrorInfo.textContent).toBe('')
  })

  it('validates the component when No AGM is checked', async () => {
    const emits = wrapper.emitted('valid')

    // check initial state
    expect(emits.length).toBe(1)
    expect(emits[0]).toEqual([true])

    // set an invalid date
    vm.$data.dateFormatted = null
    await flushPromises()

    // verify that state is now false
    expect(emits.length).toBe(2)
    expect(emits[1]).toEqual([false])

    // set No AGM
    vm.$data.didNotHoldAGM = true
    await flushPromises()

    // verify that state is now true
    expect(emits.length).toBe(3)
    expect(emits[2]).toEqual([true])
  })
})
