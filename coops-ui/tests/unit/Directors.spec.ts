import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'
import axios from '@/axios-auth'
import store from '@/store/store'

import Directors from '@/components/AnnualReport/Directors.vue'
import { EntityTypes } from '@/enums'
import { configJson } from '@/resources/business-config'

Vue.use(Vuetify)
Vue.use(Vuelidate)

// get rid of "Download the Vue Devtools extension for a better development experience" console message
Vue.config.devtools = false

// get rid of "You are running Vue in development mode" console message
Vue.config.productionTip = false

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

function click (vm: any, id: string) {
  const button = vm.$el.querySelector(id)
  const window = button.ownerDocument.defaultView
  const event = new window.Event('click')
  button.dispatchEvent(event)
}

function setValue (vm: any, id: string, value: string) {
  const input = vm.$el.querySelector(id)
  input.value = value
  const window = input.ownerDocument.defaultView
  const event = new window.Event('input')
  input.dispatchEvent(event)
}

describe('Directors as a COOP', () => {
  let vm: any
  let vm2: any

  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityType = EntityTypes.COOP
    store.state.entityFoundingDate = '2018-03-01T00:00:00'
    store.state.configObject = configJson.find(x => x.typeEnum === store.state.entityType)
    // GET directors
    sinon.stub(axios, 'get').withArgs('CP0001191/directors?date=2019-04-01')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            directors: [
              {
                'actions': [],
                'officer': {
                  'firstName': 'Peter',
                  'middleInitial': null,
                  'lastName': 'Griffin'
                },
                'id': '1',
                'deliveryAddress': {
                  'streetAddress': 'mailing_address - address line one',
                  'streetAddressAdditional': null,
                  'addressCity': 'mailing_address city',
                  'addressCountry': 'CA',
                  'postalCode': 'H0H0H0',
                  'addressRegion': 'BC',
                  'deliveryInstructions': null
                },
                'title': null
              },
              {
                'actions': [],
                'officer': {
                  'firstName': 'Joe',
                  'middleInitial': 'P',
                  'lastName': 'Swanson'
                },
                'id': '2',
                'deliveryAddress': {
                  'streetAddress': 'mailing_address - address line #1',
                  'streetAddressAdditional': 'Kirkintiloch',
                  'addressCity': 'Glasgow',
                  'addressCountry': 'UK',
                  'postalCode': 'H0H 0H0',
                  'addressRegion': 'Scotland',
                  'deliveryInstructions': 'go to the back'
                },
                'title': 'Treasurer'
              }
            ]
          }
      })))

    const Constructor = Vue.extend(Directors)
    const instance = new Constructor({ store, vuetify })
    vm = instance.$mount()

    // set as-of date
    vm.asOfDate = '2019-04-01'

    // set vm2 for draft test (setup is different and does not fire the 'asOfDate' watcher)
    store.state.currentFilingStatus = 'DRAFT'
    const instance2 = new Constructor({ store, vuetify, propsData: { asOfDate: '2019-04-01' } })
    vm2 = instance2.$mount()
  })

  afterEach(() => {
    sinon.restore()
  })

  it('initializes the director meta data properly', () => {
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].id).toEqual(1)
    expect(vm.directors[1].id).toEqual(2)
  })

  it('check the default warning message for too few directors', () => {
    expect(vm.complianceMsg).toBeDefined()
    const warning = store.state.configObject.flows.find(x => x.feeCode === 'OTCDR').warnings
    expect(vm.complianceMsg.msg).toEqual(warning.minDirectors.message)
  })

  it('check the default warning message for too few Canadian directors', () => {
    vm.directors.push({
      'actions': [],
      'officer': {
        'firstName': 'Peter',
        'middleInitial': 'P',
        'lastName': 'Parker'
      },
      'id': '3',
      'deliveryAddress': {
        'streetAddress': 'mailing_address - address line #1',
        'streetAddressAdditional': 'Kirkintiloch',
        'addressCity': 'Nanaimo',
        'addressCountry': 'CA',
        'postalCode': 'V1V 1V1',
        'addressRegion': 'BC',
        'deliveryInstructions': 'go to the back'
      },
      'title': 'Treasurer'
    })

    expect(vm.complianceMsg).toBeNull()
    vm.directors[2].deliveryAddress.addressCountry = 'UK'
    const warning = store.state.configObject.flows.find(x => x.feeCode === 'OTCDR').warnings
    expect(vm.complianceMsg.msg).toEqual(warning.canadianResident.message)
  })

  it('check the default warning message for too few directors from B.C', () => {
    vm.directors.push({
      'actions': [],
      'officer': {
        'firstName': 'Peter',
        'middleInitial': 'P',
        'lastName': 'Parker'
      },
      'id': '3',
      'deliveryAddress': {
        'streetAddress': 'mailing_address - address line #1',
        'streetAddressAdditional': 'Kirkintiloch',
        'addressCity': 'Nanaimo',
        'addressCountry': 'CA',
        'postalCode': 'V1V 1V1',
        'addressRegion': 'BC',
        'deliveryInstructions': 'go to the back'
      },
      'title': 'Treasurer'
    })

    expect(vm.complianceMsg).toBeNull()
    vm.directors[0].deliveryAddress.addressRegion = 'ON'
    vm.directors[1].deliveryAddress.addressRegion = 'ON'
    vm.directors[2].deliveryAddress.addressRegion = 'ON'
    const warning = store.state.configObject.flows.find(x => x.feeCode === 'OTCDR').warnings
    expect(vm.complianceMsg.msg).toEqual(warning.bcResident.message)
  })

  it('initializes the director name data properly', () => {
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].officer.firstName).toEqual('Peter')
    expect(vm.directors[0].officer.middleInitial).toBeNull()
    expect(vm.directors[0].officer.lastName).toEqual('Griffin')
    expect(vm.directors[0].title).toBeNull()
    expect(vm.directors[1].officer.firstName).toEqual('Joe')
    expect(vm.directors[1].officer.middleInitial).toEqual('P')
    expect(vm.directors[1].officer.lastName).toEqual('Swanson')
    expect(vm.directors[1].title).toEqual('Treasurer')
  })

  it('initializes the director address data properly', () => {
    // check complete first address
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].deliveryAddress.streetAddress).toEqual('mailing_address - address line one')
    expect(vm.directors[0].deliveryAddress.streetAddressAdditional).toEqual('')
    expect(vm.directors[0].deliveryAddress.addressCity).toEqual('mailing_address city')
    expect(vm.directors[0].deliveryAddress.addressRegion).toEqual('BC')
    expect(vm.directors[0].deliveryAddress.addressCountry).toEqual('CA')
    expect(vm.directors[0].deliveryAddress.postalCode).toEqual('H0H0H0')
    expect(vm.directors[0].deliveryAddress.deliveryInstructions).toEqual('')

    // spot-check second address
    expect(vm.directors[1].deliveryAddress.streetAddressAdditional).toEqual('Kirkintiloch')
    expect(vm.directors[1].deliveryAddress.deliveryInstructions).toEqual('go to the back')

    // Verify no mailing address for COOP directors
    expect(vm.directors[0].mailingAddress).toBeUndefined()
    expect(vm.directors[1].mailingAddress).toBeUndefined()
  })

  it('displays the list of directors', () => {
    const directorListUI = vm.$el.querySelectorAll('.director-list-item')

    expect(directorListUI[0].textContent).toContain('Peter')
    expect(directorListUI[0].textContent).toContain('Griffin')

    expect(directorListUI[1].textContent).toContain('Joe')
    expect(directorListUI[1].textContent).toContain('Swanson')

    // shows list of all directors in the UI, in reverse order in which they are in the json
    expect(directorListUI.length).toEqual(2)
    expect(directorListUI[0].textContent).toContain('Griffin')
    expect(directorListUI[0].textContent).toContain('mailing_address city')
    expect(directorListUI[1].textContent).toContain('Joe')
    expect(directorListUI[1].textContent).toContain('Glasgow')

    // shows "cease" button, indicating this is an active director, ie: starting state for list
    expect(directorListUI[0].innerHTML).toContain('<span>Cease</span>')
    expect(directorListUI[1].innerHTML).toContain('<span>Cease</span>')
  })

  it('displays the edit Director form when enabled', async () => {
    // Open the edit director
    await vm.editDirectorName(0)

    // Verify the correct data in the text input field
    expect(vm.$el.querySelectorAll('.edit-director__first-name input')[0].value).toBe('Peter')

    // Verify that only Change Name component is shown
    expect(vm.editFormShowHide.showAddress).toEqual(false)
    expect(vm.editFormShowHide.showName).toEqual(true)
    expect(vm.editFormShowHide.showDates).toEqual(false)
  })

  it('displays the edit Director form when enabled and stores the updated value', async () => {
    // Open the edit director
    await vm.editDirectorName(0)

    // Verify the correct data in the text input field
    expect(vm.$el.querySelectorAll('.edit-director__first-name input')[0].value).toBe('Peter')

    // Change the text input
    setValue(vm, '.edit-director__first-name input', 'Steve')

    // Verify that only Change Name component is shown
    expect(vm.editFormShowHide.showAddress).toEqual(false)
    expect(vm.editFormShowHide.showName).toEqual(true)
    expect(vm.editFormShowHide.showDates).toEqual(false)

    // Click and save the updated data
    await vm.saveEditDirector(0, 1)

    // Verify the updated text field value
    expect(vm.$el.querySelectorAll('.edit-director__first-name input')[0].value).toBe('Steve')
  })

  it('restores the directors name to its original value when the Cancel Edit Btn is clicked', async () => {
    // Open the edit director
    await vm.editDirectorName(0)

    // Verify the correct data in the text input field
    expect(vm.$el.querySelectorAll('.edit-director__first-name input')[0].value).toBe('Peter')

    // Change the text input
    setValue(vm, '.edit-director__first-name input', 'Steve')

    // Verify the name is updated
    expect(vm.directors[0].officer.firstName).toBe('Steve')

    // Cancel Director edit and verify the name is back to its base name
    await vm.$el.querySelectorAll('.cancel-edit-btn')[0].click()
    expect(vm.directors[0].officer.firstName).toBe('Peter')

    // Verify the edit form is closed.
    expect(vm.editFormShowHide.showAddress).toEqual(true)
    expect(vm.editFormShowHide.showName).toEqual(true)
    expect(vm.editFormShowHide.showDates).toEqual(true)
  })

  it('disables buttons/actions when instructed by parent component', done => {
    // clear enabled prop
    vm.componentEnabled = false

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(false)

      // check that first button in first director is disabled
      const directorListUI = vm.$el.querySelectorAll('.director-list-item')
      expect(directorListUI[0].querySelector('.cease-btn').disabled).toBe(true)

      // check that Appoint New Director button is not rendered
      expect(vm.$el.querySelector('.new-director-btn')).toBeNull()

      done()
    })
  })

  it('enables buttons/actions when instructed by parent component', done => {
    // set enabled prop
    vm.componentEnabled = true

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(true)

      // check that first button in first director is enabled
      const directorListUI = vm.$el.querySelectorAll('.director-list-item')
      expect(directorListUI[0].querySelector('.cease-btn').disabled).toBe(false)

      // check that Appoint New Director button is enabled
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(false)

      done()
    })
  })

  it('displays Appoint New Director form when button clicked', done => {
    // set enabled prop
    vm.componentEnabled = true

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(true)

      // check that Appoint New Director button is enabled
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(false)

      // click Appoint New Director button
      click(vm, '.new-director-btn')

      Vue.nextTick(() => {
        // check that button is hidden
        expect(vm.$el.querySelector('.new-director-btn').closest('#wrapper-add-director')
          .getAttribute('style')).toContain('height: 0px;')

        // check that form is showing
        expect(vm.$el.querySelector('.new-director')
          .getAttribute('style')).not.toContain('display: none;')

        // check that inputs are showing
        expect(vm.$el.querySelector('#new-director__first-name')).toBeDefined()
        expect(vm.$el.querySelector('#new-director__middle-initial')).toBeDefined()
        expect(vm.$el.querySelector('#new-director__last-name')).toBeDefined()

        done()
      })
    })
  })

  it('handles "ceased" action', done => {
    const directorListUI = vm.$el.querySelectorAll('.director-list-item')

    // click first director's cease button
    click(vm, '#director-1-cease-btn')

    Vue.nextTick(() => {
      // check that button has changed to "undo"
      expect(vm.$el.querySelector('#director-1-cease-btn').innerHTML).toContain('Undo')

      // check that director is marked as ceased
      expect(vm.$el.querySelector('#director-1 .director-status').innerHTML).toContain('Ceased')

      // check that director object has the 'CEASED' action
      expect(vm.directors.filter(el => el.id === 1)[0].actions).toContain('ceased')

      done()
    })
  })

  it('handles "undo ceased" action', done => {
    const directorListUI = vm.$el.querySelectorAll('.director-list-item')

    // click first director's cease button
    click(vm, '#director-1-cease-btn')

    Vue.nextTick(() => {
      // click first director's undo cease button
      click(vm, '#director-1-cease-btn')

      Vue.nextTick(() => {
        // check that button has changed back to "cease"
        expect(vm.$el.querySelector('#director-1-cease-btn').innerHTML).toContain('Cease')

        // check that director is not marked as ceased
        expect(vm.$el.querySelector('#director-1 .director-status .v-chip')
          .getAttribute('style')).toContain('display: none;')

        // check that director object does not have the 'CEASED' action
        expect(vm.directors.filter(el => el.id === 1)[0].actions).not.toContain('ceased')

        done()
      })
    })
  })

  it('initializes the original directors when status is DRAFT', done => {
    // need to setup the instance differently for this test otherwise populated by watcher fn on 'asOfDate'
    Vue.nextTick(() => {
      // check that ui got the original directors
      expect(vm2.directorsOriginal.length).toBeGreaterThan(0)

      done()
    })
  })

  // todo
  // it('can change a director\'s address', () => {
  // })

  // todo
  // it('can remove a director\'s address change', () => {
  // })

  // todo
  // it('can change a director\'s name', () => {
  // })

  // todo
  // it('can remove a director\'s name change', () => {
  // })
})

describe('Directors as a BCOMP', () => {
  let vm: any

  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0002291'
    store.state.entityType = EntityTypes.BCOMP
    store.state.configObject = configJson.find(x => x.typeEnum === store.state.entityType)
    // GET directors
    sinon.stub(axios, 'get').withArgs('CP0002291/directors?date=2019-04-01')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            directors: [
              {
                'actions': [],
                'officer': {
                  'firstName': 'Peter',
                  'middleInitial': null,
                  'lastName': 'Griffin'
                },
                'deliveryAddress': {
                  'streetAddress': 'mailing_address - address line one',
                  'streetAddressAdditional': null,
                  'addressCity': 'mailing_address city',
                  'addressCountry': 'mailing_address country',
                  'postalCode': 'H0H0H0',
                  'addressRegion': 'BC',
                  'deliveryInstructions': null
                },
                'mailingAddress': {
                  'streetAddress': '4321 Street Address',
                  'streetAddressAdditional': 'Kirkintiloch',
                  'addressCity': 'Glasgow',
                  'addressCountry': 'UK',
                  'postalCode': 'H0H 0H0',
                  'addressRegion': 'Scotland',
                  'deliveryInstructions': 'go to the back'
                },
                'title': null
              },
              {
                'actions': [],
                'officer': {
                  'firstName': 'Joe',
                  'middleInitial': 'P',
                  'lastName': 'Swanson'
                },
                'deliveryAddress': {
                  'streetAddress': '1234 MockStreet',
                  'streetAddressAdditional': 'Kirkintiloch',
                  'addressCity': 'Glasgow',
                  'addressCountry': 'UK',
                  'postalCode': 'H0H 0H0',
                  'addressRegion': 'Scotland',
                  'deliveryInstructions': 'go to the back'
                },
                'mailingAddress': {
                  'streetAddress': '1234 MockStreet',
                  'streetAddressAdditional': 'Kirkintiloch',
                  'addressCity': 'Glasgow',
                  'addressCountry': 'UK',
                  'postalCode': 'H0H 0H0',
                  'addressRegion': 'Scotland',
                  'deliveryInstructions': 'go to the back'
                },
                'title': 'Treasurer'
              }
            ]
          }
      })))

    const Constructor = Vue.extend(Directors)
    const instance = new Constructor({ store, vuetify })
    vm = instance.$mount()

    // set as-of date
    vm.asOfDate = '2019-04-01'

    // call getDirectors() since it won't be triggered from parent component
    vm.getDirectors()
  })

  afterEach(() => {
    sinon.restore()
  })

  it('initializes the director meta data properly', () => {
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].id).toEqual(1)
    expect(vm.directors[1].id).toEqual(2)
  })

  it('non-compliance due to too few directors displays accordingly', done => {
    expect(vm.complianceMsg).toBeNull()
    expect(vm.$el.querySelector('.complianceSection')).toBeNull()
    expect(vm.$el.querySelector('.warning-text')).toBeNull()
    // click first director's cease button
    click(vm, '#director-1-cease-btn')
    Vue.nextTick(() => {
    // click second director's cease button
      click(vm, '#director-2-cease-btn')
      Vue.nextTick(() => {
        expect(vm.complianceMsg.msg).toContain('A minimum of one director is required')
        expect(vm.$el.querySelector('.complianceSection')).not.toBeNull()
        expect(vm.$el.querySelector('.warning-text')).not.toBeNull()
        // un-cease director
        click(vm, '#director-2-cease-btn')
        Vue.nextTick(() => {
          expect(vm.complianceMsg).toBeNull()
          expect(vm.$el.querySelector('.complianceSection')).toBeNull()
          expect(vm.$el.querySelector('.warning-text')).toBeNull()
          done()
        })
      })
    })
  })

  it('initializes the director name data properly', () => {
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].officer.firstName).toEqual('Peter')
    expect(vm.directors[0].officer.middleInitial).toBeNull()
    expect(vm.directors[0].officer.lastName).toEqual('Griffin')
    expect(vm.directors[0].title).toBeNull()
    expect(vm.directors[1].officer.firstName).toEqual('Joe')
    expect(vm.directors[1].officer.middleInitial).toEqual('P')
    expect(vm.directors[1].officer.lastName).toEqual('Swanson')
    expect(vm.directors[1].title).toEqual('Treasurer')
  })

  it('initializes the director address data properly', () => {
    // check complete first address
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].deliveryAddress.streetAddress).toEqual('mailing_address - address line one')
    expect(vm.directors[0].deliveryAddress.streetAddressAdditional).toEqual('')
    expect(vm.directors[0].deliveryAddress.addressCity).toEqual('mailing_address city')
    expect(vm.directors[0].deliveryAddress.addressRegion).toEqual('BC')
    expect(vm.directors[0].deliveryAddress.addressCountry).toEqual('mailing_address country')
    expect(vm.directors[0].deliveryAddress.postalCode).toEqual('H0H0H0')
    expect(vm.directors[0].deliveryAddress.deliveryInstructions).toEqual('')

    // spot-check second address
    expect(vm.directors[1].deliveryAddress.streetAddressAdditional).toEqual('Kirkintiloch')
    expect(vm.directors[1].deliveryAddress.deliveryInstructions).toEqual('go to the back')

    // Spot-check mailing address
    expect(vm.directors[0].mailingAddress.streetAddress).toEqual('4321 Street Address')
    expect(vm.directors[1].mailingAddress.streetAddress).toEqual('1234 MockStreet')
  })

  it('displays the list of directors', () => {
    const directorListUI = vm.$el.querySelectorAll('.director-list-item')

    // shows list of all directors in the UI, in reverse order in which they are in the json
    expect(directorListUI.length).toEqual(2)
    expect(directorListUI[0].textContent).toContain('Griffin')
    expect(directorListUI[0].textContent).toContain('mailing_address city')
    expect(directorListUI[0].textContent).toContain('4321')
    expect(directorListUI[1].textContent).toContain('Joe')
    expect(directorListUI[1].textContent).toContain('Glasgow')
    expect(directorListUI[1].textContent).toContain('1234')
    expect(directorListUI[1].querySelector('.same-address').textContent).toContain('Same as Delivery')

    // shows "cease" button, indicating this is an active director, ie: starting state for list
    expect(directorListUI[1].innerHTML).toContain('<span>Cease</span>')
    expect(directorListUI[0].innerHTML).toContain('<span>Cease</span>')
  })

  it('disables buttons/actions when instructed by parent component', done => {
    // clear enabled prop
    vm.componentEnabled = false

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(false)

      // check that first button in first director is disabled
      const directorListUI = vm.$el.querySelectorAll('.director-list-item')
      expect(directorListUI[0].querySelector('.cease-btn').disabled).toBe(true)

      // check that Appoint New Director button is not rendered
      expect(vm.$el.querySelector('.new-director-btn')).toBeNull()

      done()
    })
  })

  it('enables buttons/actions when instructed by parent component', done => {
    // set enabled prop
    vm.componentEnabled = true

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(true)

      // check that first button in first director is enabled
      const directorListUI = vm.$el.querySelectorAll('.director-list-item')
      expect(directorListUI[0].querySelector('.cease-btn').disabled).toBe(false)

      // check that Appoint New Director button is enabled
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(false)

      done()
    })
  })

  it('displays Appoint New Director form when button clicked', done => {
    // set enabled prop
    vm.componentEnabled = true

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(true)

      // check that Appoint New Director button is enabled
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(false)

      // click Appoint New Director button
      click(vm, '.new-director-btn')

      Vue.nextTick(() => {
        // check that button is hidden
        expect(vm.$el.querySelector('.new-director-btn').closest('#wrapper-add-director')
          .getAttribute('style')).toContain('height: 0px;')

        // check that form is showing
        expect(vm.$el.querySelector('.new-director')
          .getAttribute('style')).not.toContain('display: none;')

        done()
      })
    })
  })

  it('handles "ceased" action', done => {
    const directorListUI = vm.$el.querySelectorAll('.director-list-item')

    // click first director's cease button
    click(vm, '#director-1-cease-btn')

    Vue.nextTick(() => {
      // check that button has changed to "undo"
      expect(vm.$el.querySelector('#director-1-cease-btn').innerHTML).toContain('Undo')

      // check that director is marked as ceased
      expect(vm.$el.querySelector('#director-1 .director-status').innerHTML).toContain('Ceased')

      // check that director object has the 'CEASED' action
      expect(vm.directors.filter(el => el.id === 1)[0].actions).toContain('ceased')

      done()
    })
  })

  it('handles "undo ceased" action', done => {
    const directorListUI = vm.$el.querySelectorAll('.director-list-item')

    // click first director's cease button
    click(vm, '#director-1-cease-btn')

    Vue.nextTick(() => {
      // click first director's undo cease button
      click(vm, '#director-1-cease-btn')

      Vue.nextTick(() => {
        // check that button has changed back to "cease"
        expect(vm.$el.querySelector('#director-1-cease-btn').innerHTML).toContain('Cease')

        // check that director is not marked as ceased
        expect(vm.$el.querySelector('#director-1 .director-status .v-chip')
          .getAttribute('style')).toContain('display: none;')

        // check that director object does not have the 'CEASED' action
        expect(vm.directors.filter(el => el.id === 1)[0].actions).not.toContain('ceased')

        done()
      })
    })
  })
})

describe('Appoint New Director tests', () => {
  let vm: any

  beforeEach(() => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityType = EntityTypes.COOP

    // GET directors
    sinon.stub(axios, 'get').withArgs('CP0001191/directors?date=2019-04-01')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            directors: []
          }
      })))

    const Constructor = Vue.extend(Directors)
    const instance = new Constructor({ store, vuetify })
    vm = instance.$mount()

    // set props
    vm.asOfDate = '2019-04-01'
    vm.componentEnabled = true

    // click Appoint New Director button
    click(vm, '.new-director-btn')
  })

  afterEach(() => {
    sinon.restore()
  })

  it('accepts valid First Name', done => {
    setValue(vm, '#new-director__first-name', 'First First')
    expect(vm.director.officer.firstName).toBe('First First')

    // verify that there are no validation errors
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[0].textContent).toBe('')
      done()
    }, 250)
  })

  it('displays error for invalid First Name - leading spaces', done => {
    setValue(vm, '#new-director__first-name', '  First')
    expect(vm.director.officer.firstName).toBe('  First')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[0].textContent).toContain('Invalid spaces')
      done()
    }, 250)
  })

  it('displays error for invalid First Name - trailing spaces', done => {
    setValue(vm, '#new-director__first-name', 'First  ')
    expect(vm.director.officer.firstName).toBe('First  ')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[0].textContent).toContain('Invalid spaces')
      done()
    }, 250)
  })

  it('allows First Name with multiple inline spaces', done => {
    setValue(vm, '#new-director__first-name', 'First  First')
    expect(vm.director.officer.firstName).toBe('First  First')

    // verify that validation error is not displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[0].textContent).toBe('')
      done()
    }, 250)
  })

  it('accepts valid Middle Initial', done => {
    setValue(vm, '#new-director__middle-initial', 'M M')
    expect(vm.director.officer.middleInitial).toBe('M M')

    // verify that there are no validation errors
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[1].textContent).toBe('')
      done()
    }, 250)
  })

  it('displays error for invalid Middle Initial - leading spaces', done => {
    setValue(vm, '#new-director__middle-initial', '  M')
    expect(vm.director.officer.middleInitial).toBe('  M')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[1].textContent).toContain('Invalid spaces')
      done()
    }, 250)
  })

  it('displays error for invalid Middle Initial - trailing spaces', done => {
    setValue(vm, '#new-director__middle-initial', 'M  ')
    expect(vm.director.officer.middleInitial).toBe('M  ')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[1].textContent).toContain('Invalid spaces')
      done()
    }, 250)
  })

  it('allows Middle Initial with multiple inline spaces', done => {
    setValue(vm, '#new-director__middle-initial', 'M  M')
    expect(vm.director.officer.middleInitial).toBe('M  M')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[1].textContent).toBe('')
      done()
    }, 250)
  })

  it('accepts valid Last Name', done => {
    setValue(vm, '#new-director__last-name', 'Last')
    expect(vm.director.officer.lastName).toBe('Last')

    // verify that there are no validation errors
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[2].textContent).toBe('')
      done()
    }, 250)
  })

  it('displays error for invalid Last Name - leading spaces', done => {
    setValue(vm, '#new-director__last-name', '  Last')
    expect(vm.director.officer.lastName).toBe('  Last')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[2].textContent).toContain('Invalid spaces')
      done()
    }, 250)
  })

  it('displays error for invalid Last Name - trailing spaces', done => {
    setValue(vm, '#new-director__last-name', 'Last  ')
    expect(vm.director.officer.lastName).toBe('Last  ')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[2].textContent).toContain('Invalid spaces')
      done()
    }, 250)
  })

  it('allows Last Name with multiple inline spaces', done => {
    setValue(vm, '#new-director__last-name', 'Last  Last')
    expect(vm.director.officer.lastName).toBe('Last  Last')

    // verify that validation error is displayed
    setTimeout(() => {
      expect(vm.$el.querySelectorAll('.v-messages')[2].textContent).toBe('')
      done()
    }, 250)
  })

  // todo
  // it('can appoint a new director', () => {
  // })

  // todo
  // it('can edit a new director', () => {
  // })

  // todo
  // it('can remove a new director', () => {
  // })
})
