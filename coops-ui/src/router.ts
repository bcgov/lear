import Vue from 'vue'
import VueRouter from 'vue-router'
import AnnualReport from '@/views/AnnualReport.vue'
import Dashboard from '@/views/Dashboard.vue'
import axios from '@/axios-auth'

Vue.use(VueRouter)
var authURL
var payAPIURL
var authAPIURL
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
      authURL = JSON.parse(req.responseText)['AUTH_URL']
      console.log('Set authURL to: ' + authURL)
      authAPIURL = JSON.parse(req.responseText)['AUTH_API_URL']
      console.log('Set authURL to: ' + authAPIURL)
      payAPIURL = JSON.parse(req.responseText)['PAY_API_URL']
      console.log('Set authURL to: ' + payAPIURL)
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
      get authURL () {
        return authURL
      },
      get authAPIURL () {
        return authAPIURL
      },
      get payAPIURL () {
        return payAPIURL
      }
    }
  }
})

window.addEventListener('message', function (e) {
  if (e.origin === authURL) { // assumes authURL does not have slash if referrer URL does not have slash
    const data = JSON.parse(e.data)
    sessionStorage.setItem('KEYCLOAK_TOKEN', data['access_token'])
    sessionStorage.setItem('KEYCLOAK_REFRESH_TOKEN', data['refresh_token'])
    sessionStorage.setItem('REGISTRIES_TRACE_ID', data['registries_trace_id'])
    sessionStorage.setItem('REDIRECTED', 'false')
  }
})

let router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: Dashboard,
      meta: {
        requiresAuth: true
      }
    },
    {
      path: '/annual-report',
      name: 'annual-report',
      component: AnnualReport,
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
    },
    {
      // default/fallback route
      path: '*',
      redirect: '/'
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
