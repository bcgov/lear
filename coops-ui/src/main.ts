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

// FOR TESTING ONLY!!!
// eslint-disable-next-line
// sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI3ZGJkZmFkMC1mODQ1LTRjMTAtYWM1YS03NDMyYWVhNzhlZDUiLCJleHAiOjE1NzUwODAyMTEsIm5iZiI6MCwiaWF0IjoxNTc1MDUxNDExLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiI4ZTVkZDYzNS01OGRkLTQ5YzUtYmViMS00NmE1ZDVhMTYzNWMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiIzMzM5ZDU4OC1mODRjLTQ3YjktYTdlOC1iNWU5ZGNkMWZmMjEiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImJjMDAwNzI5MSIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImJjMDAwNzI5MSJ9.BpspQqhgnOulqpTJbBs6U0Q7616SpOwRMarzdhyp1GzhAX6oM93wa8oePM3Cob6fotvQ3tcJb08LQrevdU8LX61CxTNL9hXQJa1bvJKRO2PnYVhmZD0Q0Ir1yT-BCfoJh33DFpOG0M11XD6nHfpx2KdCfRl_HEQ4hbqGrc06hsRZ2tQCl4a0sPrGtDqBlpz6z-PFuiRjVCMEu5Yze3ttHT46VXtIIXFV3fJj0w2sI56011rLR1UVOFBuU7GmvVZPDHLknAvtlkBCSRQhvCXT_4st2X7IP891NEsZt4nksX6AveKB_ODNFxvW6wrrsF_Faxs80Rzlt32h5WM8BQTWQg')
// sessionStorage.setItem('BUSINESS_IDENTIFIER', 'BC0007291')
// sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

// // FOR TESTING ONLY!!!
// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiJmYTFmYWJlZS1mOTQyLTRkMDctYjhjNS1jNGNmZWQzY2EzNjQiLCJleHAiOjE1NzUwNzk2NjQsIm5iZiI6MCwiaWF0IjoxNTc1MDUwODY0LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiJjM2Y0YWYxMS1hMjVlLTQ2YjEtOGJhNi1kOGZkNjMwZmY0NzUiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI0YTQxYzdlMC02Njg2LTQ3MTEtODBkYi0zYjMzMjQ1NzQwMWEiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTMyNyIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTMyNyJ9.fAOk8GfgE6taQ6BduTpmV2YCjVYKFZ-3HCtKUwB0f_XIAnft1YJe5uULyrkxWzGW_qq8fnxASJ_KVbaYOjBSu4n0Vl1d16aHFMJbwG7u_BXx4LC81CzkYpZoZnEPvZp0xhg4x9L4gj_4dLlhX8UfpK6OVw4-l9O71CHbH47dNHbeaHIUJocEt8C-tsLenAuA7Qi3eNnL6KETrs7Cw-kqshaacLV2J-3Lq-5HT9WXM8cRFRG6kXEDKXG1KaQ2-oF_pX7P_96FInKz1DMir-P2lXEd3zzXZpAjU78kVe7qikKBPZCt353nSLRHbpHF_kbgJOQASsJrrZknHMRVpFqJ2g')
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001327')
sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

/**
 * first fetch config from server, then load Vue
 */
configHelper.fetchConfig()
  .then(() => {
    // ensure we have a Keycloak token
    if (!sessionStorage.getItem('KEYCLOAK_TOKEN')) {
      console.log('Redirecting to Auth URL...')
      const authUrl = sessionStorage.getItem('AUTH_URL')
      // assume Auth URL is always reachable
      window.location.assign(authUrl)
      return // do not execute remaining code
    }
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
