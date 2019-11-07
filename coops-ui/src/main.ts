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
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI5MmMwZjMyYi0wYTE5LTRmMDItYTM5My0zZTExMTE1OGJjY2MiLCJleHAiOjE1NzMxNzE2NjMsIm5iZiI6MCwiaWF0IjoxNTczMTQyODYzLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiIwOTNkODNkZC02OTU2LTQ1Y2EtODg5Zi0xN2UzYjFiYmU2NmMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJub25jZSI6ImE4Njc0MzQ5LTQzNjctNGI4Ny04NTQxLTc1ZDZiYjc4MWQ1YSIsImF1dGhfdGltZSI6MTU3MzE0Mjg2Miwic2Vzc2lvbl9zdGF0ZSI6IjkwYTJkZmMxLWFhN2ItNDU4MC1hNWM3LWI4MjQ4MjMzZmNmNCIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwLyIsIjE5Mi4xNjguMC4xMyIsIioiLCJodHRwOi8vMTkyLjE2OC4wLjEzOjgwODAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCIsImZpcnN0bmFtZSI6IkJDUkVHVEVTVCBEYWxpYSIsInJvbGVzIjpbInB1YmxpY191c2VyIiwiZWRpdCIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXSwibmFtZSI6IkJDUkVHVEVTVCBEYWxpYSBPTkUiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJiY3NjL2JoZ3Y1MjVjYWFvNnVqanZxdmM3cnFoczJlZWEyb2QzIiwibG9naW5Tb3VyY2UiOiJCQ1NDIiwibGFzdG5hbWUiOiJPTkUiLCJ1c2VybmFtZSI6ImJjc2MvYmhndjUyNWNhYW82dWpqdnF2YzdycWhzMmVlYTJvZDMifQ.OVM7g4VXcFfzjniiubsIBxuoR9FB9fxJbGeruAhELNtlHxPofF1gkFbCd4y6A4unwqPnShXE_46RBNIHlJTlhJAy0jwTSWGo7FctxsGgqVJ5AN41iPfGT6l3R5nawUFbKDLW6yVYrzjUxE1_o5iubAX0--Qos6VOnk5Pw5F4pHyI42f2MASQvgYQc_GiBjbWDFsHtwoE3s1y9O4aqoFtLS-krLj2Jy6J7qjLiRzlDJrxAknM43deXQ1N7Pr6AY7r9FBgY7r58C-VIco1i8A573XISEAY8voERJr1lCKxWwMmCLRUNN9ixTIF46lQBVdiG0-8GVtbX4ONVADudjO2UQ')
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
