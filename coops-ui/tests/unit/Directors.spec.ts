import Vue from 'vue'
import Vuetify from 'vuetify'

import App from '@/App.vue'
import Home from '@/views/Home.vue'
import Directors from '@/components/ARSteps/Directors.vue'
import store from '@/store'
import sinon from 'sinon'
import axios from '@/axios-auth.ts'
import Vuelidate from 'vuelidate'
Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('Directors.vue', () => {
  // just need a token that can get parsed properly (will be expired but doesn't matter for tests)
  // note - the corp num in this token is CP0001191
  sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N' +
    '3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIxYzQ2YjIzOS02ZWY0LTQxYTQtYThmMy05N2M5M2IyNmNlMjAiLCJle' +
    'HAiOjE1NTcxNzMyNTYsIm5iZiI6MCwiaWF0IjoxNTU3MTY5NjU2LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2' +
    'EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJzYmMtYXV0aC13ZWIiLCJzdWIiOiIwMzZlN2I4Ny0zZTQxLTQ2MTMtYjFiYy04NWU5OTA' +
    'xNTgzNzAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJkOGZmYjk4' +
    'OS0zNzRlLTRhYTktODc4OS03YTRkODA1ZjNkOTAiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6O' +
    'DA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl' +
    '0IiwidW1hX2F1dGhvcml6YXRpb24iLCJiYXNpYyJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY' +
    '291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTE5MSJ9.Ou' +
    'JLtzYCnkp5KXSiudGFJY6hTSvdE3KokhkEzqU-icxAzQwZSTYbzZQdGsIScy4-DIWHahIGp9L-e6mYlQSQta2rK2Kte85MxThubyw0096UOtAE' +
    'wnS9VURHXPUm4ZUyI4ECkyLlFywOPxAftNdeSYeJx26GHBCvo6uR9Zv6A3yTlJy3B1HJxBWk_6xTAzGPPDCLoyKGeIxGidGujKCKCAfXRMrjhX' +
    'yBv90XzDgZ-To-6_jMjSjBX6Dtq7icdZYLWWDdrhjCpJA5CKS0PlSgeH1Yq4rHd8Ztp5cvVdJFxt87gIopIOQvcy4ji0gtaovgUhiyg07gXGl8' +
    'dGZwn1tpLA')
  let rootvm
  let vm
  let childvm

  let click = function (id) {
    console.log('ID: ', id)
    let button = childvm.$el.querySelector(id)
    let window = button.ownerDocument.defaultView
    var click = new window.Event('click')
    button.dispatchEvent(click)
  }
  beforeEach((done) => {
    // reset store
    store.state.agmDate = null
    store.state.filedDate = null
    store.state.validated = false
    store.state.noAGM = false
    store.state.corpNum = 'CP0001191'

    // GET current directors list
    sinon.stub(axios, 'get').withArgs('CP0001191/directors')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            directors: [
              {
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

    const RootConstructor = Vue.extend(App)
    let rootInstance = new RootConstructor({ store: store })
    rootvm = rootInstance.$mount()

    const Constructor = Vue.extend(Home)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()

    const ChildConstructor = Vue.extend(Directors)
    let childInstance = new ChildConstructor({ store: store })
    childvm = childInstance.$mount()

    // call getDirectors() since it won't be triggered from parent component
    childvm.getDirectors()

    setTimeout(() => {
      done()
    }, 100)
  })

  afterEach((done) => {
    sinon.restore()
    setTimeout(() => {
      done()
    }, 500)
  })

  it('initializes the director meta data properly', () => {
    expect(childvm.directors.length).toEqual(2)
    expect(childvm.directors[0].id).toEqual(1)
    expect(childvm.directors[0].isNew).toEqual(false)
    expect(childvm.directors[0].isDirectorActive).toEqual(true)
    expect(childvm.directors[1].id).toEqual(2)
    expect(childvm.directors[1].isNew).toEqual(false)
    expect(childvm.directors[1].isDirectorActive).toEqual(true)
  })

  it('initializes the director name data properly', () => {
    expect(childvm.directors.length).toEqual(2)
    expect(childvm.directors[0].officer.firstName).toEqual('Peter')
    expect(childvm.directors[0].officer.middleInitial).toBeNull()
    expect(childvm.directors[0].officer.lastName).toEqual('Griffin')
    expect(childvm.directors[0].title).toBeNull()
    expect(childvm.directors[1].officer.firstName).toEqual('Joe')
    expect(childvm.directors[1].officer.middleInitial).toEqual('P')
    expect(childvm.directors[1].officer.lastName).toEqual('Swanson')
    expect(childvm.directors[1].title).toEqual('Treasurer')
  })

  it('initializes the director address data properly', () => {
    // check complete first address
    expect(childvm.directors.length).toEqual(2)
    expect(childvm.directors[0].deliveryAddress.streetAddress).toEqual('mailing_address - address line one')
    expect(childvm.directors[0].deliveryAddress.streetAddressAdditional).toBeNull()
    expect(childvm.directors[0].deliveryAddress.addressCity).toEqual('mailing_address city')
    expect(childvm.directors[0].deliveryAddress.addressRegion).toEqual('BC')
    expect(childvm.directors[0].deliveryAddress.addressCountry).toEqual('mailing_address country')
    expect(childvm.directors[0].deliveryAddress.postalCode).toEqual('H0H0H0')
    expect(childvm.directors[0].deliveryAddress.deliveryInstructions).toBeNull()

    // spot-check second address
    expect(childvm.directors[1].deliveryAddress.streetAddressAdditional).toEqual('Kirkintiloch')
    expect(childvm.directors[1].deliveryAddress.deliveryInstructions).toEqual('go to the back')
  })

  it('displays the list of directors', () => {
    var directorListUI = childvm.$el.querySelectorAll('.director-list .container')

    // shows list of all directors in the UI
    expect(directorListUI.length).toEqual(2)
    expect(directorListUI[0].textContent).toContain('Griffin')
    expect(directorListUI[0].textContent).toContain('mailing_address city')
    expect(directorListUI[1].textContent).toContain('Joe')
    expect(directorListUI[1].textContent).toContain('Glasgow')

    // shows "cease" button, indicating this is an active director, ie: starting state for list
    expect(directorListUI[0].innerHTML).toContain('<span>Cease</span>')
    expect(directorListUI[1].innerHTML).toContain('<span>Cease</span>')
  })

  it('buttons/actions are disabled when the AGM date has not been set', () => {
    var directorListUI = childvm.$el.querySelectorAll('.director-list .container')

    // confirm that flag is set correctly
    expect(childvm.agmEntered).toEqual(false)

    // check that buttons are disabled (checks first button in first director, plus the Add New Director button)
    expect(
      directorListUI[0].querySelector('.actions .v-btn').attributes.getNamedItem('disabled').value
    ).toEqual('disabled')
    expect(
      childvm.$el.querySelector('.new-director-btn').attributes.getNamedItem('disabled').value
    ).toEqual('disabled')
  })

  it('buttons/actions are enabled when the AGM date has been set', () => {
    var directorListUI = childvm.$el.querySelectorAll('.director-list .container')

    // set AGM Date in AGMDate component
    childvm.$store.state.agmDate = '2018-06-18'

    setTimeout(() => {
      // confirm that flag is set correctly
      expect(childvm.agmEntered).toEqual(true)

      // check that buttons are enabled (checks first button in first director, plus the Add New Director button)
      expect(
        directorListUI[0].querySelector('.actions .v-btn').attributes.getNamedItem('disabled')
      ).toBeNull()
      expect(
        childvm.$el.querySelector('.new-director-btn').attributes.getNamedItem('disabled')
      ).toBeNull()
    }, 100)
  })

  it('buttons/actions are enabled when "No AGM" option set', () => {
    var directorListUI = childvm.$el.querySelectorAll('.director-list .container')

    // set "No AGM" in AGMDate component
    childvm.$store.state.noAGM = true

    setTimeout(() => {
      // confirm that flag is set correctly
      expect(childvm.agmEntered).toEqual(true)

      // check that buttons are enabled (checks first button in first director, plus the Add New Director button)
      expect(
        directorListUI[0].querySelector('.actions .v-btn').attributes.getNamedItem('disabled')
      ).toBeNull()
      expect(
        childvm.$el.querySelector('.new-director-btn').attributes.getNamedItem('disabled')
      ).toBeNull()
    }, 100)
  })

  it('displays Add New Director form when button clicked', () => {
    // todo
  })
  it('handles "ceased" action', () => {
    // todo
  })
  it('handles un-"ceased" action', () => {
    // todo
  })

  it('adds a new director to list', () => {
    // todo
  })
  it('can undo adding new director', () => {
    // todo
  })
})
