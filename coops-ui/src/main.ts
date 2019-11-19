import 'core-js/stable' // to polyfill ECMAScript features
import 'regenerator-runtime/runtime' // to use transpiled generator functions
import '@mdi/font/css/materialdesignicons.min.css' // ensure you are using css-loader
import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import App from '@/App.vue'
import Vuelidate from 'vuelidate'
import Vue2Filters from 'vue2-filters'
import Affix from 'vue-affix'
import router from '@/router'
import store from '@/store/store'
import configHelper from '@/utils/config-helper'
import '@/registerServiceWorker'
import { withFlagProvider } from 'ld-vue'

const opts = { iconfont: 'mdi' }

Vue.use(Vuetify)
Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)
Vue.config.productionTip = false

// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI2MjZlM2NkNS0yZDAzLTQzOGQtYTJlMy1hMGNlNmZmNmEyMmYiLCJleHAiOjE1NzQyMjI0MjgsIm5iZiI6MCwiaWF0IjoxNTc0MTkzNjI4LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiIxZTJlYjk0Mi02YjZmLTRlZWItYmYzNy04ZjA1NTdjYTQ5MzgiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI3ZWQxYmIxNS01YzRmLTRhOTMtYTRlOC1iYjk5YjdhMzg4MWIiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTIwNSIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTIwNSJ9.eGMq9cBNcRa43lxDqHTBRJa88ZcoXLCoqnkbKtNw0yYPEpJ0F6B13z3lRgtNJEpjegkCcBMKRcE5dMdGlLJWbR74FXu-SA9CJxPtVmDQevhT-b06-F3giJNtj5KKZ2jFWUiWt1OUGkYdvXOJFABhydRi8V2M8V7fAFGnstH5nQDbnU0srlKsbJyfCI6MRXUI-BooBa_NvVboL2Y7GdRFUGgAbV6hUQcrWAMHUzRGNkCwae7hNfSiqtvJSfQlaC57p4bcbafVLcryCMhk8yyeSfGlbQE_SRbINdxsdG_54ZsFNf4JwFyyESxulVHzG7AZLbDMhE_0QUOOYcSToOzzOw')
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001205')
sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

/**
 * first fetch config from server, then load Vue
 */

configHelper.fetchConfig()
  .then(() => {
    new Vue({
      vuetify: new Vuetify(opts),
      router,
      store,
      mixins: [withFlagProvider({ clientSideId: window['ldClientId'] })],
      render: h => h(App)
    }).$mount('#app')
  })
  .catch(error => {
    console.error('error fetching config -', error)
    alert('Fatal error loading app')
  })
