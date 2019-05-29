import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import axios from '@/axios-auth'

Vue.use(Router)
var payURL
var authURL
/* load configurations from file */
var req = new XMLHttpRequest()
// TODO - change request to async:true once UI is more complete - currently too quick because we jump straight to AR
req.open('GET', '/config/configuration.json', false)
req.setRequestHeader('Accept', 'application/json')
req.setRequestHeader('ResponseType', 'application/json')
req.onreadystatechange = function (response) {
  if (req.readyState === 4) {
    if (req.status === 200) {
      axios.defaults.baseURL = JSON.parse(req.responseText)['API_URL']
      console.log('Set axios.baseURL to: ' + axios.defaults.baseURL)
      payURL = JSON.parse(req.responseText)['PAY_URL']
      console.log('Set payURL to: ' + payURL)
      authURL = JSON.parse(req.responseText)['AUTH_URL']
      console.log('Set authURL to: ' + authURL)
    } else {
      // nothing
      console.log('could not load configurations')
    }
  }
}
req.send()
Vue.mixin({
  data: function () {
    return {
      get payURL () {
        return payURL
      },
      get authURL () {
        return authURL
      }
    }
  }
})

window.addEventListener('message', function (e) {
  if (e.origin === authURL) {
    sessionStorage.setItem('KEYCLOAK_TOKEN', e.data)
    sessionStorage.setItem('REDIRECTED', 'false')
  }
})

let router = new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: {
        requiresAuth: true
      }
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (about.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import(/* webpackChunkName: "about" */ './views/About.vue')
    }
  ]
})
router.afterEach((to, from) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    console.log('redirect check ', sessionStorage.getItem('REDIRECTED'))
    if (sessionStorage.getItem('REDIRECTED') !== 'true') {
      let auth = sessionStorage.getItem('KEYCLOAK_TOKEN')
      if (auth) {
        console.log('AUTH PASSED')
      } else {
        console.log('AUTH FAILED')
        sessionStorage.setItem('REDIRECTED', 'true')
        window.location.href = authURL
      }
    }
  }
})

export default router
