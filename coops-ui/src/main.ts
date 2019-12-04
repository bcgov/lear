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
import App from '@/App.vue'

// get rid of "You are running Vue in development mode" console message
Vue.config.productionTip = false

Vue.use(Vuetify)
Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)

const vuetify = new Vuetify({ iconfont: 'mdi' })

// FOR TESTING ONLY!!!
// eslint-disable-next-line
// sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiJkZTAwNzAwYy0wZGJmLTQ0OTktOTI4NS0zMjFiYzAwMmQzY2UiLCJleHAiOjE1NzU1MDY0MDksIm5iZiI6MCwiaWF0IjoxNTc1NDc3NjA5LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiJjM2Y0YWYxMS1hMjVlLTQ2YjEtOGJhNi1kOGZkNjMwZmY0NzUiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiIyNmIxMjYyOS0yZTA5LTQyM2EtYTUyYi01ODdjZjU0ZDljZDIiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTMyNyIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTMyNyJ9.VBga7jZwBwefE6B-mBncTON1RDljzqcILve9dmDKxOm-zkWozFWGrvcrv9-HVzyIo25L2uCBhhZcMtA-a5W75rb0mXfihl3KQ2CBxdkpzcqBwTm_8x6dg6uUbDWocWTKc5UHHffg-3rF-o9XstJDdh5qeag0ALiG0Tjb-EdYKt5tYkmlU6A-Qtx5dbQ1VDn3LGcTrTHnUtk5gnaCoKsvJ9cEP3z-snbt5sVBs4uT7nUJvGx02H3TG8vt6RXRSHVvZa0G5rHY4SLDZhL-j9caYPCy4vwrMhxm42U53ISmVmb6QG3GvlNiQBzzY0DT9afRBhcBbD_b7OHA9Su78FWENw')
// sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001327')
// sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

// FOR TESTING ONLY!!!
// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI1NzJkYWM1MS1lMGJiLTRiMTAtYTFlNy1kZGEwOGViNDA4MTYiLCJleHAiOjE1NzU1MDQ3OTgsIm5iZiI6MCwiaWF0IjoxNTc1NDc1OTk4LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiI4ZTVkZDYzNS01OGRkLTQ5YzUtYmViMS00NmE1ZDVhMTYzNWMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJiMzcyYzRhNi1lODlhLTQyZjEtYjc1Mi1kNWMxMzM0ZmZjNjIiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImJjMDAwNzI5MSIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImJjMDAwNzI5MSJ9.OX7mUoX5IFF4_3J05M4zoxbNMEqCKn-QTujjJL3A4k28jvQdSs1LxG7mGKC5XjkE8F1PnT2HfIpbBI9lqOnCJhVdcU55u0d8wnYGyNpXAz4KYigq9f7VRlzw48e-2FGr3cboDKc7T_8XHgL10SRo20zslByrXkTQV5_bVLub5tR8zINppcR6fdgBmW-lM4typhQ28gbYmdN4dyuUagSltTZjL1KRQIrllmlCF9a3zeRwYMeYrok4EKZQuEzKrv41P_gZHEFF7L0Yqanm0Xm3Sc8z-cIXD62qzNxlZAuva4ZQ2rukAOTuBYcR0S3Q9olEaM5efyq8lJ5FaklSRkYTgg')
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'BC0007291')
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
      vuetify,
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
