import 'core-js/stable' // to polyfill ECMAScript features
import 'regenerator-runtime/runtime' // to use transpiled generator functions
import '@mdi/font/css/materialdesignicons.min.css' // ensure you are using css-loader
import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import Vuelidate from 'vuelidate'
import Vue2Filters from 'vue2-filters'
import Affix from 'vue-affix'
import configHelper from '@/utils/config-helper'
import router from '@/router'
import store from '@/store/store'
import { withFlagProvider } from 'ld-vue'
import '@/registerServiceWorker'
import '@/assets/styles/base.scss'
import '@/assets/styles/layout.scss'
import '@/assets/styles/overrides.scss'
import TokenServices from '@/services/token-services'
import App from '@/App.vue'

// get rid of "You are running Vue in development mode" console message
Vue.config.productionTip = false

Vue.use(Vuetify)
Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)

const vuetify = new Vuetify({ iconfont: 'mdi' })

// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiJhOTk1NDRkMi0xMDNkLTQ0MTktYWVjYS1kNjhmYWU4MTZjZjIiLCJleHAiOjE1NzY3MDg3NjcsIm5iZiI6MCwiaWF0IjoxNTc2NzA2OTY3LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiI2YjhkNzc1ZS0zOTdiLTQwYTctYjc2YS04N2E3MmQ3MjU2ZTUiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJub25jZSI6Ijc0OTE3MTAyLTU3MTMtNDgzZi1hMmM0LWNjOWI0NjUwMThmZSIsImF1dGhfdGltZSI6MTU3NjcwNjk2Niwic2Vzc2lvbl9zdGF0ZSI6IjA3MTcyZWFkLTJhYjMtNGUwYS04MTdhLTI4ODMwMWZiMjU2YiIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwLyIsIjE5Mi4xNjguMC4xMyIsIioiLCJodHRwOi8vMTkyLjE2OC4wLjEzOjgwODAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCIsImZpcnN0bmFtZSI6IkJDUkVHVEVTVCBMaW4iLCJyb2xlcyI6WyJwdWJsaWNfdXNlciIsImVkaXQiLCJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl0sIm5hbWUiOiJCQ1JFR1RFU1QgTGluIFRXRU5UWVRIUkVFIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiYmNzYy93dnhwa3pzb3B1NmJpcWN6YW01Mm40N203Z21jazZvZCIsImxvZ2luU291cmNlIjoiQkNTQyIsImxhc3RuYW1lIjoiVFdFTlRZVEhSRUUiLCJ1c2VybmFtZSI6ImJjc2Mvd3Z4cGt6c29wdTZiaXFjemFtNTJuNDdtN2dtY2s2b2QifQ.F7VtuD0cpCJF2gpj8yHKNsewBH-j6AmJy_9__nMqQnp8vN_nrJKepRwcYqWNN0jwmqo3cYW3fPgrf8D-R_WIJxN9NKmlgCG0SWMx3cdYQzDK95AHz46RXwPYz_5XH1hba5RP23l7rw8gBUV4DNBFYB4YC6LczL1gXPQ8mgJCmhmPugClybEFWGK6ngx8zqaHcr_n7Lz-zdGKO10dNl4ncIFScN6qY2cfxmLmDh7Z7fI7tLc5NG4SkbWfk9QG-zpYahKXmLdXhb-YS0sJGD0y-lFJjB8-lPtajIRRCVWcUQ8bvOABivm2yeRrEdrnIht8JTF473e3BZXd8K1-FO6_Ow')
// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_REFRESH_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI0YjYxZGViZi01M2NlLTQxODMtYWFhMS1jMmU2NjQxMDNhZWQifQ.eyJqdGkiOiJiZTBhOGI0YS1kMTJjLTQzMjAtOGNmNC0zNDVhNjMzMjM1MjAiLCJleHAiOjE1NzY3MzU3NjcsIm5iZiI6MCwiaWF0IjoxNTc2NzA2OTY3LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJzdWIiOiI2YjhkNzc1ZS0zOTdiLTQwYTctYjc2YS04N2E3MmQ3MjU2ZTUiLCJ0eXAiOiJSZWZyZXNoIiwiYXpwIjoic2JjLWF1dGgtd2ViIiwibm9uY2UiOiI3NDkxNzEwMi01NzEzLTQ4M2YtYTJjNC1jYzliNDY1MDE4ZmUiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiIwNzE3MmVhZC0yYWIzLTRlMGEtODE3YS0yODgzMDFmYjI1NmIiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsicHVibGljX3VzZXIiLCJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIn0.NHu5-Mu1-bVvXA0QrHZBATySA1EQ62c7p7Dr56_bhgE')
// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_ID_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIyYzRhOWFjOC04NmM4LTRmN2QtYTU5Yi01ODdiMTgxYmM3MTgiLCJleHAiOjE1NzY3MDg3NjcsIm5iZiI6MCwiaWF0IjoxNTc2NzA2OTY3LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJzYmMtYXV0aC13ZWIiLCJzdWIiOiI2YjhkNzc1ZS0zOTdiLTQwYTctYjc2YS04N2E3MmQ3MjU2ZTUiLCJ0eXAiOiJJRCIsImF6cCI6InNiYy1hdXRoLXdlYiIsIm5vbmNlIjoiNzQ5MTcxMDItNTcxMy00ODNmLWEyYzQtY2M5YjQ2NTAxOGZlIiwiYXV0aF90aW1lIjoxNTc2NzA2OTY2LCJzZXNzaW9uX3N0YXRlIjoiMDcxNzJlYWQtMmFiMy00ZTBhLTgxN2EtMjg4MzAxZmIyNTZiIiwiYWNyIjoiMSIsImZpcnN0bmFtZSI6IkJDUkVHVEVTVCBMaW4iLCJuYW1lIjoiQkNSRUdURVNUIExpbiBUV0VOVFlUSFJFRSIsInByZWZlcnJlZF91c2VybmFtZSI6ImJjc2Mvd3Z4cGt6c29wdTZiaXFjemFtNTJuNDdtN2dtY2s2b2QiLCJsb2dpblNvdXJjZSI6IkJDU0MiLCJsYXN0bmFtZSI6IlRXRU5UWVRIUkVFIiwidXNlcm5hbWUiOiJiY3NjL3d2eHBrenNvcHU2YmlxY3phbTUybjQ3bTdnbWNrNm9kIn0.O-eTnW7mw_DolqNr-73LCynUIfDi2ZDCOTGGw7gI8nyoH3oLwJnhG-4iKZHOj7_29TERTPkmYhNn_x7jfopGf18gOOXVTOy4vuQaomzDtTYEcfxLzZa72xbYN5oDywblgV8CMux06k94JoLiPXwyFmLvcX4IITW7-i4XqIgFW3IhGLZLsq994YebGSa7BPashKx90wVjBZ-lOvQvtoWrgST6U9wmDGSgd4xGyzOS042ZE64VPLbajb_2Z9YBiPXKbpt5fa0u1984QMoOqhQzT016fqsw6A7c41tpkwXUVtaxeNFsZXmSFMPAmEgKBSX-VpP9P5gjkmydwlHA7Atlng')
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001364')
sessionStorage.setItem('USER_FULL_NAME', 'Firstname Lastname')

/**
 * first fetch config from server, then load Vue
 */
configHelper.fetchConfig()
  .then(() => {
    // ensure we have the necessary Keycloak tokens
    if (!haveKcTokens()) {
      console.info('Redirecting to Auth URL...')
      const authUrl = sessionStorage.getItem('AUTH_URL')
      // assume Auth URL is always reachable
      window.location.assign(authUrl)
      return // do not execute remaining code
    }

    // start token service to refresh KC token periodically
    console.info('Starting token refresh service...')
    const tokenServices = new TokenServices()
    tokenServices.initUsingUrl(sessionStorage.getItem('KEYCLOAK_CONFIG_URL'))
      .then(() => tokenServices.scheduleRefreshTimer())
      .catch(err => console.error(err))

    new Vue({
      vuetify,
      router,
      store,
      mixins: [withFlagProvider({ clientSideId: window['ldClientId'] })],
      render: h => h(App)
    }).$mount('#app')
  })
  .catch(error => {
    console.error('Error fetching config -', error)
    alert('Fatal error loading app')
  })

function haveKcTokens (): boolean {
  return Boolean(sessionStorage.getItem('KEYCLOAK_TOKEN') &&
    sessionStorage.getItem('KEYCLOAK_REFRESH_TOKEN') &&
    sessionStorage.getItem('KEYCLOAK_ID_TOKEN'))
}
