import Vue from 'vue'
import VueRouter from 'vue-router'
import AnnualReport from '@/views/AnnualReport.vue'
import Dashboard from '@/views/Dashboard.vue'
import axios from '@/axios-auth'

Vue.use(VueRouter)

let authURL: string
let payAPIURL: string
let authAPIURL: string

/* load configurations from file */
const req = new XMLHttpRequest()
// TODO - change request to async:true once UI is more complete - currently too quick because we jump straight to AR
req.open('GET', '/config/configuration.json', false)
req.setRequestHeader('Accept', 'application/json')
req.setRequestHeader('ResponseType', 'application/json')
req.onreadystatechange = function () {
  if (req.readyState === XMLHttpRequest.DONE) {
    if (req.status === 200) {
      const configuration = JSON.parse(req.responseText)

      axios.defaults.baseURL = configuration['API_URL']
      console.log('Set axios.defaults.baseURL to: ' + axios.defaults.baseURL)

      authURL = configuration['AUTH_URL']
      console.log('Set authURL to: ' + authURL)

      authAPIURL = configuration['AUTH_API_URL']
      console.log('Set authAPIURL to: ' + authAPIURL)

      payAPIURL = configuration['PAY_API_URL']
      console.log('Set payAPIURL to: ' + payAPIURL)

      window['addressCompleteKey'] = configuration['ADDRESS_COMPLETE_KEY']
      console.log('Set addressCompleteKey')
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
