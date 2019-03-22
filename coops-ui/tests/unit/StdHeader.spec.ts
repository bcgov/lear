import Vue from 'vue'
import Vuetify from 'vuetify'

import StdHeader from '@/components/StdHeader.vue'
Vue.use(Vuetify)

describe('StdHeader.vue', () => {
  const Constructor = Vue.extend(StdHeader)
  let instance = new Constructor()
  let vm = instance.$mount()

  let click = function (id: string) {
    console.log('ID: ', id)
    let target = vm.$el.querySelector(id)
    var click = new Event('click')
    target.dispatchEvent(click)
  }

  beforeEach((done) => {
    setTimeout(() => {
      done()
    }, 100)
  })

  afterEach((done) => {
    setTimeout(() => {
      done()
    }, 100)
  })

  describe.skip('login button', () => {
    it('shows login button when not logged in', () => {
      // add tests here
    })
    it('does not show login button when logged in', () => {
      // add tests here
    })

    it('goes to login page when login button clicked', () => {
      // click the login link/button
      click('#login-button')
      setTimeout(() => {
        // add tests here
      }, 10)
    })
  })
})
