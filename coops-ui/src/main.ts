import 'core-js/stable' // to polyfill ECMAScript features
import 'regenerator-runtime/runtime' // to use transpiled generator functions
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

const opts = { iconfont: 'mdi' }

Vue.use(Vuetify)
Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)
Vue.config.productionTip = false

// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIyYjkwZTkyMi05NDVhLTQ3M2UtOTBlNy0wZmNkMDE3YzFjMzYiLCJleHAiOjE1NzA5MDUyNDMsIm5iZiI6MCwiaWF0IjoxNTcwODE4ODQzLCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiJhMjU3MDUyZC1lOWM0LTRkN2MtODdhYy1hNDEwYjc2ODMwOGMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiIxN2RiNTYwZC02Y2Q4LTRkNmQtOWU0NS1mMDczOTU2NTViMzMiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTI1MiIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTI1MiJ9.GUoRYGtPqInO-XNP4yQ4EtXPRkUvIsm7WSSgJljjKTI3S_ruwTbit-Z8kGy0ttT4sy2vccQiWKREMabFH41M7wv08iASe_WmI9WzbPAskTOUWYu1iFtj79nu_m6wHS88RQl5bsqrD0nahb6887GWR7MY73B3TuFMn19JxvlPTUICTEjA4iCBWoVdBlV1p8TKWIP1poc94flOahBJUbmKxZLZWsGxKEpCPzH1Pk-UC8Hatrn-EskXkVoMxL8CiMRSSuBAQVR9fSvDcRXjM-hu6NanMysJiwU5X_RdkBHUrK_DO8PV4ej6-gaGcQRsROZ0WWa3FfvkiMJWuEMjQQ7OUA')     // <<< paste in JWT
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001252')

/**
 * first fetch config from server, then load Vue
 */
configHelper.fetchConfig()
  .then(() => {
    new Vue({
      vuetify: new Vuetify(opts),
      router,
      store,
      render: h => h(App)
    }).$mount('#app')
  })
  .catch(error => {
    console.error('error fetching config -', error)
    alert('Fatal error loading app')
  })
