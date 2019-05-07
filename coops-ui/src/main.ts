import '@babel/polyfill'
import Vue from 'vue'
import App from './App.vue'
import axios from './axios-auth'
import Vuelidate from 'vuelidate'
import router from './router'
import store from './store'
import './plugins/vuetify'
import './registerServiceWorker'

Vue.use(Vuelidate)
Vue.config.productionTip = false

window.addEventListener('message', function (e) {
  if (e.origin === process.env.VUE_APP_AUTH_URL) {
    sessionStorage.setItem('KEYCLOAK_TOKEN', e.data)
    sessionStorage.setItem('REDIRECTED', 'false')
  }
})
/* load configurations from file */
var req = new XMLHttpRequest()
// TODO - change request to async:true once UI is more complete - currently too quick because we jump straight to AR
req.open('GET', '/config/configuration.json', false)
req.setRequestHeader('Accept', 'application/json')
req.setRequestHeader('ResponseType', 'application/json')
req.onreadystatechange = function (response) {
  if (req.readyState === 4) {
    if (req.status === 200) {
      axios.defaults.baseURL = process.env.VUE_APP_API_URL
      console.log('Setting axios.baseURL to: ' + axios.defaults.baseURL)
    } else {
      // nothing
      console.log('could not load configurations')
    }
  }
}
req.send()
/* end load configs */

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
