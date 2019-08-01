import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import flushPromises from 'flush-promises'

import store from '@/store/store'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AGMDate.vue', () => {
  let vm

  beforeEach(async () => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2017

    const Constructor = Vue.extend(AGMDate)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()

    await flushPromises()
  })

  it('initializes the local variables properly', () => {
    expect(vm.$data.date).toBe('2017-01-01')
    expect(vm.$data.dateFormatted).toBe('2017/01/01')
    expect(vm.$data.didNotHoldAGM).toBe(false)
    expect(vm.$data.agmDateValid).toBe(true)

    // verify checkbox
    expect(vm.$el.querySelector('#agm-checkbox')).toBeDefined()

    // verify global state
    expect(vm.$store.state.agmDateValid).toBe(true)
  })

  it('sets date picker when text field is set', async () => {
    vm.$data.dateFormatted = '2017/05/12'

    await flushPromises()

    // check local variable
    expect(vm.$data.date).toBe('2017-05-12')

    // check global variable
    expect(vm.agmDate).toBe('2017-05-12')
  })

  it('sets text field when date picker is set', async () => {
    vm.$data.date = '2017-12-05'

    await flushPromises()

    // check local variable
    expect(vm.$data.dateFormatted).toBe('2017/12/05')

    // check global variable
    expect(vm.agmDate).toBe('2017-12-05')
  })

  it('doesn\'t render checkbox in current year', async () => {
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    await flushPromises()

    expect(vm.$el.querySelector('#agm-checkbox')).toBeNull()
  })

  it('invalidates the component when date is empty', async () => {
    vm.$data.dateFormatted = ''

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(vm.$el.querySelector('.v-messages').textContent)
      .toContain('An Annual General Meeting date is required.')
  })

  it('invalidates the component when entered format is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid length
    vm.$data.dateFormatted = '2017/06/1'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

    // invalid first slash
    vm.$data.dateFormatted = '2017.06/15'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

    // invalid second slash
    vm.$data.dateFormatted = '2017/06.15'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

    // invalid third slash
    vm.$data.dateFormatted = '2017/06///'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')
  })

  it('invalidates the component when entered year is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid year
    vm.$data.dateFormatted = '2018/01/01'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a date within 2017.')
  })

  it('invalidates the component when entered month is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid month number
    vm.$data.dateFormatted = '2019/13/01'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a valid month in the past.')

    // invalid future month
    vm.$data.dateFormatted = '2019/08/15'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a valid month in the past.')
  })

  it('invalidates the component when entered day is invalid', async () => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    // check initial state (date was initialized to 2019/01/01)
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid day number (Feb 29 on non leap year)
    vm.$data.dateFormatted = '2019/02/29'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a valid day in the past.')

    // invalid day number (future day)
    vm.$data.dateFormatted = '2019/07/20'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(false)
    expect(validationErrorInfo.textContent).toContain('Please enter a valid day in the past.')

    // valid day number (day in the past, this year, with day number > current day number)
    vm.$data.dateFormatted = '2019/06/20'

    await flushPromises()

    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')
  })

  it('validates the component when No AGM is checked', async () => {
    // set an invalid date
    vm.$data.dateFormatted = null

    await flushPromises()

    // verify that state is now false
    expect(vm.$store.state.agmDateValid).toBe(false)

    // set No AGM
    vm.$data.didNotHoldAGM = true

    await flushPromises()

    // verify that state is now true
    expect(vm.$store.state.agmDateValid).toBe(true)
  })
})
