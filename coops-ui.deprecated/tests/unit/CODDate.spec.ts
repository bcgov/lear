import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import { mount } from '@vue/test-utils'

import store from '@/store/store'
import CodDate from '@/components/StandaloneDirectorChange/CODDate.vue'

Vue.config.silent = true

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// get rid of "Download the Vue Devtools extension for a better development experience" console message
Vue.config.devtools = false

// get rid of "You are running Vue in development mode" console message
Vue.config.productionTip = false

describe('CodDate', () => {
  let wrapper
  let vm

  beforeEach(() => {
    // init store
    store.state.currentDate = '2019/07/15'

    // set Last Filing Date and verify new Min Date
    store.state.entityFoundingDate = '2018-03-01T00:00:00'

    wrapper = mount(CodDate, { store, vuetify })
    vm = wrapper.vm as any
  })

  afterEach(() => {
    wrapper.destroy()
    wrapper = null
  })

  it('loads variables properly when initial COD Date is set', () => {
    wrapper.setProps({ initialCODDate: '2019-05-10' })

    // verify local variables
    expect(vm.$data.date).toBe('2019-05-10')
    expect(vm.$data.dateFormatted).toBe('2019/05/10')

    // verify emitted COD Date
    const codDates = wrapper.emitted('codDate')
    expect(codDates.length).toBe(1)
    expect(codDates[0]).toEqual(['2019-05-10'])

    // verify emitted Valid
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(1)
    expect(valids[0]).toEqual([true])
  })

  it('sets Min Date properly based on global properties', () => {
    // verify initial state
    expect(vm.$store.state.filings).toEqual([])
    expect(vm.$store.state.lastPreLoadFilingDate).toBeNull()

    // verify default Min Date
    expect(vm.minDate).toBe('2018-03-01')

    // set Last Filing Date and verify new Min Date
    store.state.filings = [
      { filing: { header: { date: '2019-02-01' }, changeOfDirectors: {} } },
      { filing: { header: { effectiveDate: '2019-03-01' }, changeOfDirectors: {} } }
    ]
    expect(vm.minDate).toBe('2019-03-01')

    // cleanup
    store.state.filings = []
    store.state.lastPreLoadFilingDate = null
  })

  it('sets Min Date to entity founding date if no filings are present', () => {
    // verify initial state
    expect(vm.$store.state.filings).toEqual([])

    expect(vm.minDate).toBe('2018-03-01')
  })

  it('sets Max Date to current date in store', () => {
    expect(vm.maxDate).toBe(vm.$store.state.currentDate.split('/').join('-'))
  })

  it('Shows error message when date has invalid length', () => {
    wrapper.setData({ dateFormatted: '2019/11/6' })
    expect(vm.$data.date).toBe('')
    expect(vm.$el.querySelector('.v-messages').textContent).toContain('A Director change date is required.')
  })

  it('sets date picker and emits date changed and valid events when date is changed', () => {
    wrapper.setData({ dateFormatted: '2019/05/10' })

    // verify local variables
    expect(vm.$data.date).toBe('2019-05-10')

    wrapper.setData({ dateFormatted: '2019/05/11' })

    // verify local variables
    expect(vm.$data.date).toBe('2019-05-11')

    // verify emitted COD Dates
    // first emit is from init
    // second emit is from text field update
    const codDates = wrapper.emitted('codDate')
    expect(codDates.length).toBe(2)
    expect(codDates[0]).toEqual(['2019-05-10'])
    expect(codDates[1]).toEqual(['2019-05-11'])

    // verify emitted Valids
    // first emit is from init
    // second emit is from text field update
    const valids = wrapper.emitted('valid')
    expect(valids.length).toBe(2)
    expect(valids[0]).toEqual([true])
    expect(valids[1]).toEqual([true])
  })

  it('invalidates the component when entered month is after Max Date', () => {
    wrapper = mount(CodDate, { store,
      vuetify,
      computed: {
        minDate () {
          return '2019-01-01'
        },
        maxDate () {
          return '2019-05-05'
        }
      } })

    wrapper.setData({ dateFormatted: '2019/11/11' })
    wrapper.vm.$v.$touch()
    expect(wrapper.vm.$v.dateFormatted.isValidCODDate).toBe(false)
  })

  it('invalidates the component when entered month is before Min Date', () => {
    wrapper = mount(CodDate, { store,
      vuetify,
      computed: {
        minDate () {
          return '2019-01-01'
        },
        maxDate () {
          return '2019-05-05'
        }
      } })

    wrapper.setData({ dateFormatted: '2018/11/11' })
    wrapper.vm.$v.$touch()
    expect(wrapper.vm.$v.dateFormatted.isValidCODDate).toBe(false)
  })
})
