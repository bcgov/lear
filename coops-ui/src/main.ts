import 'core-js/stable' // to polyfill ECMAScript features
import 'regenerator-runtime/runtime' // to use transpiled generator functions
import '@mdi/font/css/materialdesignicons.css'
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
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIzYzEyNzlkYi03Y2Y4LTQ0YjUtYjM5ZS0zZjUzNmM4YzY0NzgiLCJleHAiOjE1NzMyNTg2MTQsIm5iZiI6MCwiaWF0IjoxNTczMjI5ODE0LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiIwOTNkODNkZC02OTU2LTQ1Y2EtODg5Zi0xN2UzYjFiYmU2NmMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJub25jZSI6ImE1NjE0Y2ViLTAzNGEtNDhlNS05Y2MyLTE3ZDQ1Mjg4MTY3NiIsImF1dGhfdGltZSI6MTU3MzIyOTgxMiwic2Vzc2lvbl9zdGF0ZSI6IjJkMTJmMzNlLWE1YTMtNGNiZC04MDE3LWY4ZTg3ODE2Njg1MiIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwLyIsIjE5Mi4xNjguMC4xMyIsIioiLCJodHRwOi8vMTkyLjE2OC4wLjEzOjgwODAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCIsImZpcnN0bmFtZSI6IkJDUkVHVEVTVCBEYWxpYSIsInJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXSwibmFtZSI6IkJDUkVHVEVTVCBEYWxpYSBPTkUiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJiY3NjL2JoZ3Y1MjVjYWFvNnVqanZxdmM3cnFoczJlZWEyb2QzIiwibG9naW5Tb3VyY2UiOiJCQ1NDIiwibGFzdG5hbWUiOiJPTkUiLCJ1c2VybmFtZSI6ImJjc2MvYmhndjUyNWNhYW82dWpqdnF2YzdycWhzMmVlYTJvZDMifQ.aRdr-rwRCZGqFW-QqJxdAidoD2qFUKovGUNk4wUUFrEOZZ1ykUhLAUcK1nUXszwzQcEt_BrttG_BI78nsVKxUafnectQmzlqS6ppc0adglC55SbRRBfmGIBdA6H_0yyJi_dbhs7GcGouyl-gmLajOxXN3-QrWuIc60E-TtDFi7H_sBQCH90ph5-VSy3HiQ4AHc5CT3tfwzrPFyciSbjI0J0Swj0I8bL4oSDmciP8EOmcbFIgAgK-ODLMyoEO7O3hBRil2xSl0Y16Ap5TFcKrRDpNrXc83R5CxgKsjg8bOJlcRWsd0Bx44eYemvhUQR8nHWF5-PP8a9tNpGeu_Tubew')
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'BC0007291')

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
