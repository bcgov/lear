import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'

import store from '@/store/store'
import AGMDate from '@/components/AnnualReport/AGMDate.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('AGMDate.vue', () => {
  let vm

  function click (id) {
    const button = vm.$el.querySelector(id)
    const window = button.ownerDocument.defaultView
    const click = new window.Event('click')
    button.dispatchEvent(click)
  }

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2017

    const Constructor = Vue.extend(AGMDate)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
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

    console.log('Passed Test 1')
  })

  it('sets date picker when text field is set', done => {
    vm.$data.dateFormatted = '2017/05/12'

    Vue.nextTick(() => {
      // check local variable
      expect(vm.$data.date).toBe('2017-05-12')

      // check global variable
      expect(vm.agmDate).toBe('2017-05-12')

      console.log('Passed Test 2')
      done()
    })
  })

  it('sets text field when date picker is set', done => {
    vm.$data.date = '2017-12-05'

    Vue.nextTick(() => {
      // check local variable
      expect(vm.$data.dateFormatted).toBe('2017/12/05')

      // check global variable
      expect(vm.agmDate).toBe('2017-12-05')

      console.log('Passed Test 3')
      done()
    })
  })

  it('doesn\'t render checkbox in current year', done => {
    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#agm-checkbox')).toBeNull()
      console.log('Passed Test 4')
      done()
    })
  })

  it('invalidates the component when date is empty', done => {
    vm.$data.dateFormatted = ''

    Vue.nextTick(() => {
      expect(vm.$store.state.agmDateValid).toBe(false)
      expect(vm.$el.querySelector('.v-messages').textContent)
        .toContain('An Annual General Meeting date is required.')

      console.log('Passed Test 5')
      done()
    })
  })

  it('invalidates the component when entered format is invalid', done => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid length
    vm.$data.dateFormatted = '2017/06/1'

    Vue.nextTick(() => {
      expect(vm.$store.state.agmDateValid).toBe(false)
      expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

      // invalid first slash
      vm.$data.dateFormatted = '2017.06/15'

      Vue.nextTick(() => {
        expect(vm.$store.state.agmDateValid).toBe(false)
        expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

        // invalid second slash
        vm.$data.dateFormatted = '2017/06.15'

        Vue.nextTick(() => {
          expect(vm.$store.state.agmDateValid).toBe(false)
          expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

          // invalid third slash
          vm.$data.dateFormatted = '2017/06///'

          Vue.nextTick(() => {
            expect(vm.$store.state.agmDateValid).toBe(false)
            expect(validationErrorInfo.textContent).toContain('Date must be in format YYYY/MM/DD.')

            console.log('Passed Test 6')
            done()
          })
        })
      })
    })
  })

  it('invalidates the component when entered year is invalid', done => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid year
    vm.$data.dateFormatted = '2018/01/01'

    Vue.nextTick(() => {
      expect(vm.$store.state.agmDateValid).toBe(false)
      expect(validationErrorInfo.textContent).toContain('Please enter a date within 2017.')

      console.log('Passed Test 7')
      done()
    })
  })

  it('invalidates the component when entered month is invalid', done => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid month number
    vm.$data.dateFormatted = '2019/13/01'

    Vue.nextTick(() => {
      expect(vm.$store.state.agmDateValid).toBe(false)
      expect(validationErrorInfo.textContent).toContain('Please enter a valid month in the past.')

      // invalid future month
      vm.$data.dateFormatted = '2019/08/15'

      Vue.nextTick(() => {
        expect(vm.$store.state.agmDateValid).toBe(false)
        expect(validationErrorInfo.textContent).toContain('Please enter a valid month in the past.')

        console.log('Passed Test 8')
        done()
      })
    })
  })

  it('invalidates the component when entered day is invalid', done => {
    const validationErrorInfo = vm.$el.querySelector('.validationErrorInfo')

    store.state.currentDate = '2019/07/15'
    store.state.ARFilingYear = 2019

    // check initial state
    expect(vm.$store.state.agmDateValid).toBe(true)
    expect(validationErrorInfo.textContent).toBe('')

    // invalid day number
    vm.$data.dateFormatted = '2019/02/29'

    Vue.nextTick(() => {
      expect(vm.$store.state.agmDateValid).toBe(false)
      expect(validationErrorInfo.textContent).toContain('Please enter a valid day in the past.')

      // invalid future day
      vm.$data.dateFormatted = '2019/07/16'

      Vue.nextTick(() => {
        expect(vm.$store.state.agmDateValid).toBe(false)
        expect(validationErrorInfo.textContent).toContain('Please enter a valid day in the past.')

        console.log('Passed Test 9')
        done()
      })
    })
  })

  it('validates the component when No AGM is checked', done => {
    // set an invalid date
    vm.$data.dateFormatted = null

    Vue.nextTick(() => {
      // verify that state is now false
      expect(vm.$store.state.agmDateValid).toBe(false)

      // set No AGM
      vm.$data.didNotHoldAGM = true

      Vue.nextTick(() => {
        // verify that state is now true
        expect(vm.$store.state.agmDateValid).toBe(true)

        console.log('Passed Test 10')
        done()
      })
    })
  })
})
