import Vue from 'vue'
import Vuetify from 'vuetify'

import StdHeader from '@/components/StdHeader.vue'

Vue.use(Vuetify)

describe('StdHeader.vue', () => {
  let vm

  function click (id) {
    const button = vm.$el.querySelector(id)
    const window = button.ownerDocument.defaultView
    // const click = new Event('click')
    const click = new window.Event('click')
    button.dispatchEvent(click)
  }

  beforeEach(done => {
    const constructor = Vue.extend(StdHeader)
    const instance = new constructor()
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  it('displays the title', () => {
    expect(vm.$el.querySelector('.bcros').textContent).toEqual('BC Registries & Online Services')
  })

  describe.skip('login button', () => {
    it('shows login button when not logged in', () => {
      // TODO - add tests here
    })

    it('does not show login button when logged in', () => {
      // TODO - add tests here
    })

    it('goes to login page when login button clicked', done => {
      // click the login link/button
      click('#login-button')

      Vue.nextTick(() => {
        // TODO - add tests here
        done()
      })
    })
  })
})
