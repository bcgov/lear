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
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIwZWI3MzVhNy1hZGQyLTRlZDgtYjc3ZC00ZjZlYTZhZDFjNjUiLCJleHAiOjE1NzMwODQ1NTMsIm5iZiI6MCwiaWF0IjoxNTczMDU1NzUzLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiIwOTNkODNkZC02OTU2LTQ1Y2EtODg5Zi0xN2UzYjFiYmU2NmMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJub25jZSI6IjZmYmVlY2ZhLTY4ZjItNDY1Yy04YjMwLTdiMGU0OThhOTcyMCIsImF1dGhfdGltZSI6MTU3MzA1NTc1Miwic2Vzc2lvbl9zdGF0ZSI6Ijc4MDQwNmUxLTRiMmYtNDEzZS1iMWEyLTA3OGYyNmM3YzQwNCIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwLyIsIjE5Mi4xNjguMC4xMyIsIioiLCJodHRwOi8vMTkyLjE2OC4wLjEzOjgwODAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCIsImZpcnN0bmFtZSI6IkJDUkVHVEVTVCBEYWxpYSIsInJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXSwibmFtZSI6IkJDUkVHVEVTVCBEYWxpYSBPTkUiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJiY3NjL2JoZ3Y1MjVjYWFvNnVqanZxdmM3cnFoczJlZWEyb2QzIiwibG9naW5Tb3VyY2UiOiJCQ1NDIiwibGFzdG5hbWUiOiJPTkUiLCJ1c2VybmFtZSI6ImJjc2MvYmhndjUyNWNhYW82dWpqdnF2YzdycWhzMmVlYTJvZDMifQ.QY-goTxjOB6WVSEdoJBc2lpJBzk0-5R4ci5mwZXJnAt8QbWGhSizrqvGO_XZplfaW-LkCmESE3WjRdLAMkgHQXtqziFbDHhXArafh1lpl-7jPwLCpXWOl_QIxGIfXtrbD8_u0UvT0-0uAsxUf94OOS4X_ZvsqndHoC8DzbqpViZVkhdm926QSeNgrsvUWtk9rQsj9o9QuRFqR9NXgcAoSNmQIPv2k-ztm15oSLnDvJ7fMlLbYoeKveUSkvZNTc1Esgi043lWIu1QjoBGuiDafHZGVj5v2ZkiN4pT77Qbx8B88zq4RzpOSQe_GWZWhNXogjn4KQ3oKClXBexcSldOAg')
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
