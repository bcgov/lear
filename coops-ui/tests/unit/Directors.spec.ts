import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import Directors from '@/components/AnnualReport/Directors.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('Directors', () => {
  let vm

  function click (id) {
    const button = vm.$el.querySelector(id)
    const window = button.ownerDocument.defaultView
    const click = new window.Event('click')
    button.dispatchEvent(click)
  }

  beforeEach(done => {
    // init store
    store.state.entityIncNo = 'CP0001191'

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
                'deliveryAddress': {
                  'streetAddress': 'mailing_address - address line one',
                  'streetAddressAdditional': null,
                  'addressCity': 'mailing_address city',
                  'addressCountry': 'mailing_address country',
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
    const instance = new Constructor({ store: store })
    vm = instance.$mount()

    // set as-of date
    vm.asOfDate = '2019-04-01'

    // call getDirectors() since it won't be triggered from parent component
    vm.getDirectors()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('initializes the director meta data properly', () => {
    expect(vm.directors.length).toEqual(2)
    expect(vm.directors[0].id).toEqual(1)
    expect(vm.directors[1].id).toEqual(2)
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
  })

  it('displays the list of directors', () => {
    const directorListUI = vm.$el.querySelectorAll('.director-list .container')

    // shows list of all directors in the UI, in reverse order in which they are in the json
    expect(directorListUI.length).toEqual(2)
    expect(directorListUI[1].textContent).toContain('Griffin')
    expect(directorListUI[1].textContent).toContain('mailing_address city')
    expect(directorListUI[0].textContent).toContain('Joe')
    expect(directorListUI[0].textContent).toContain('Glasgow')

    // shows "cease" button, indicating this is an active director, ie: starting state for list
    expect(directorListUI[0].innerHTML).toContain('<span>Cease</span>')
    expect(directorListUI[1].innerHTML).toContain('<span>Cease</span>')
  })

  it('disables buttons/actions when instructed by parent component', done => {
    // invalidate AGM Date
    vm.componentEnabled = false

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(false)

      const directorListUI = vm.$el.querySelectorAll('.director-list .container')

      // check that buttons are disabled (checks first button in first director, plus the Add New Director button)
      expect(directorListUI[0].querySelector('.cease-btn').disabled).toBe(true)
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(true)

      done()
    })
  })

  it('enables buttons/actions when instructed by parent component', done => {
    // validate AGM Date
    vm.componentEnabled = true

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(true)

      const directorListUI = vm.$el.querySelectorAll('.director-list .container')

      // check that buttons are enabled (checks first button in first director, plus the Add New Director button)
      expect(directorListUI[0].querySelector('.cease-btn').disabled).toBe(false)
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(false)

      done()
    })
  })

  it('displays Add New Director form when button clicked', done => {
    // validate AGM Date
    vm.componentEnabled = true

    Vue.nextTick(() => {
      // confirm that flag is set correctly
      expect(vm.componentEnabled).toEqual(true)

      // check that Add New Director button is enabled
      expect(vm.$el.querySelector('.new-director-btn').disabled).toBe(false)

      // click Add New Director button
      click('.new-director-btn')

      Vue.nextTick(() => {
        // check that button is hidden
        expect(vm.$el.querySelector('.new-director-btn').closest('div')
          .getAttribute('style')).toContain('height: 0px;')

        // check that form is showing
        expect(vm.$el.querySelector('.new-director')
          .getAttribute('style')).not.toContain('display: none;')

        done()
      })
    })
  })

  it('handles "ceased" action', done => {
    const directorListUI = vm.$el.querySelectorAll('.director-list .container')

    // click first director's cease button
    click('#director-1-cease-btn')

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

  it('handles un-"ceased" action', done => {
    const directorListUI = vm.$el.querySelectorAll('.director-list .container')

    // click first director's cease button
    click('#director-1-cease-btn')

    Vue.nextTick(() => {
      // click first director's undo cease button
      click('#director-1-cease-btn')

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

  // todo
  // it('adds a new director to list', () => {
  // })

  // todo
  // it('can undo adding new director', () => {
  // })
})
