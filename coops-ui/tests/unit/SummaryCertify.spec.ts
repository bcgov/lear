// Libraries
import Vue from 'vue'
import Vuetify from 'vuetify'
import { mount, Wrapper } from '@vue/test-utils'

// Components
import { SummaryCertify } from '@/components/Common'

// Store
import store from '@/store/store'

Vue.use(Vuetify)
let vuetify = new Vuetify({})

const statementSelector: string = '.certify-content'
const someCertifier = 'Some Certifier'
const defaultDate = '2019-01-01'

/**
 * Creates and mounts a component, so that it can be tested.
 *
 * @param certifiedBy the value to pass to the component for the name input. The default value is "undefined".
 * @param isCertified the value to pass to the component for the checkbox. The default value is "undefined".
 * @param currentDate the value to pass to the component for the static date. The default value is defaultDate.
 *
 * @returns a Wrapper<Certify> object with the given parameters.
 */
function createComponent (certifiedBy: string = undefined, isCertified: boolean = undefined,
  currentDate: string = defaultDate): Wrapper<SummaryCertify> {
  return mount(SummaryCertify, { sync: false,
    propsData: {
      'certifiedBy': certifiedBy,
      'currentDate': currentDate,
      'isCertified': isCertified
    } })
}

describe('SummaryCertified', () => {
  let vm

  beforeEach(done => {
    const Constructor = Vue.extend(SummaryCertify)
    const instance = new Constructor({ store: store, vuetify })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  it('has date displayed', () => {
    const wrapper: Wrapper<SummaryCertify> = createComponent()

    // The text should contain the date.
    expect(wrapper.text()).toEqual(expect.stringMatching(new RegExp(defaultDate)))
  })

  it('has statement with certifier', () => {
    const wrapper: Wrapper<SummaryCertify> = createComponent(someCertifier)
    const statement: Wrapper<Vue> = wrapper.find(statementSelector)

    // The text should contain the certifier name.
    expect(statement.text()).toEqual(expect.stringMatching(new RegExp(someCertifier)))
  })

  it('has statement with trimmed certifier', () => {
    const untrimmedCertifier = '   ' + someCertifier + ' '
    const wrapper: Wrapper<SummaryCertify> = createComponent(untrimmedCertifier)
    const statement: Wrapper<Vue> = wrapper.find(statementSelector)

    // The text should contain the certifier name.
    expect(statement.text()).toEqual(expect.not.stringMatching(new RegExp(untrimmedCertifier)))
  })
})
