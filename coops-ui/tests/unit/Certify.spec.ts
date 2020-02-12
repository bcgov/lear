//
// Copyright © 2019 Province of British Columbia
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
// the License. You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//

import Vue from 'vue'
import Vuetify from 'vuetify'
import store from '@/store/store'
import { mount, Wrapper } from '@vue/test-utils'

import Certify from '@/components/AnnualReport/Certify.vue'

Vue.use(Vuetify)

// Input field selectors to test changes to the DOM elements.
const certifiedBySelector: string = 'input[type=text]'
const isCertifiedSelector: string = 'input[type=checkbox]'
const statementSelector: string = '.certify-stmt'

const trimmedCertifier = 'Some Certifier'
const whitespaceCertifier = '  Some  Certifier  '
const defaultDate = '2019-01-01'

/**
 * Returns the last event for a given name, to be used for testing event propagation in response to component changes.
 *
 * @param wrapper the wrapper for the component that is being tested.
 * @param name the name of the event that is to be returned.
 *
 * @returns the value of the last named event for the wrapper.
 */
function getLastEvent (wrapper: Wrapper<Certify>, name: string): any {
  const eventsList: Array<any> = wrapper.emitted(name)
  const events: Array<any> = eventsList[eventsList.length - 1]

  return events[0]
}

/**
 * Creates and mounts a component, so that it can be tested.
 *
 * @param certifiedBy the value to pass to the component for the name input. The default value is "undefined".
 * @param isCertified the value to pass to the component for the checkbox. The default value is "undefined".
 * @param currentDate the value to pass to the component for the static date. The default value is defaultDate.
 *
 * @returns a Wrapper<Certify> object with the given parameters.
 */
function createComponent (
  certifiedBy: string = undefined,
  isCertified: boolean = undefined,
  currentDate: string = defaultDate
): Wrapper<Certify> {
  store.state.currentDate = currentDate

  return mount(Certify, {
    store,
    sync: false,
    propsData: {
      certifiedBy,
      isCertified
    }
  })
}

describe('Certify', () => {
  it('has date displayed', () => {
    const wrapper: Wrapper<Certify> = createComponent()

    // The text should contain the date.
    expect(wrapper.text()).toContain(defaultDate)
  })

  it('has statement with certifier', () => {
    const wrapper: Wrapper<Certify> = createComponent(trimmedCertifier)
    const statement: Wrapper<Vue> = wrapper.find(statementSelector)

    // The text should contain the certifier name.
    expect(statement.text()).toContain(trimmedCertifier)
  })

  it('has statement with trimmed certifier', () => {
    const wrapper: Wrapper<Certify> = createComponent(whitespaceCertifier)
    const statement: Wrapper<Vue> = wrapper.find(statementSelector)

    // The text should contain the trimmed certifier name.
    expect(statement.text()).toContain(trimmedCertifier)
  })

  it('is invalid when no props are defined', () => {
    const wrapper: Wrapper<Certify> = createComponent()

    // The last "valid" event should indicate that the form is invalid.
    expect(getLastEvent(wrapper, 'valid')).toBe(false)
  })

  it('is invalid when just certifiedBy is defined', () => {
    const wrapper: Wrapper<Certify> = createComponent(trimmedCertifier, undefined)

    // The last "valid" event should indicate that the form is invalid.
    expect(getLastEvent(wrapper, 'valid')).toBe(false)
  })

  it('is invalid when just isCertified is defined', () => {
    const wrapper: Wrapper<Certify> = createComponent(undefined, true)

    // The last "valid" event should indicate that the form is invalid.
    expect(getLastEvent(wrapper, 'valid')).toBe(false)
  })

  it('is valid when both certifiedBy and isCertified are defined', () => {
    const wrapper: Wrapper<Certify> = createComponent(trimmedCertifier, true)

    // The last "valid" event should indicate that the form is valid.
    expect(getLastEvent(wrapper, 'valid')).toBe(true)
  })

  it('is valid when certifier is defined and contains whitespace', () => {
    const wrapper: Wrapper<Certify> = createComponent(whitespaceCertifier, true)

    // The last "valid" event should indicate that the form is valid.
    expect(getLastEvent(wrapper, 'valid')).toBe(true)
  })

  it('is invalid when certifier is just whitespace', () => {
    const wrapper: Wrapper<Certify> = createComponent('  ', true)

    // The last "valid" event should indicate that the form is invalid.
    expect(getLastEvent(wrapper, 'valid')).toBe(false)
  })

  it('is still invalid when certifier is just whitespace and form is certified', () => {
    const wrapper: Wrapper<Certify> = createComponent('  ', false)
    const checkboxElement: Wrapper<Vue> = wrapper.find(isCertifiedSelector)
    checkboxElement.setChecked()

    // The last "valid" event should indicate that the form is invalid.
    expect(getLastEvent(wrapper, 'valid')).toBe(false)
  })

  it('has update event for certifiedBy', () => {
    const wrapper: Wrapper<Certify> = createComponent()
    const inputElement: Wrapper<Vue> = wrapper.find(certifiedBySelector)
    inputElement.setValue(trimmedCertifier)

    // The last "update:certifiedBy" event should match the input.
    expect(getLastEvent(wrapper, 'update:certifiedBy')).toMatch(trimmedCertifier)
  })

  it('has update event for trimmed certifiedBy', () => {
    const wrapper: Wrapper<Certify> = createComponent()
    const inputElement: Wrapper<Vue> = wrapper.find(certifiedBySelector)
    inputElement.setValue(whitespaceCertifier)

    // The last "update:certifiedBy" event should be a trimmed version of the input.
    expect(getLastEvent(wrapper, 'update:certifiedBy')).toMatch(trimmedCertifier)
  })

  it('has update event for isCertified', () => {
    const wrapper: Wrapper<Certify> = createComponent()
    const checkboxElement: Wrapper<Vue> = wrapper.find(isCertifiedSelector)
    checkboxElement.setChecked()

    // The last "update:isCertified" event should indicate that the checkbox is checked.
    expect(getLastEvent(wrapper, 'update:isCertified')).toBe(true)
  })
})
