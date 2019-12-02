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
// sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIzOGM5NmFjOC1mOTUyLTQxYmQtYjgzYS1jYTU2YWFhNzc3MWMiLCJleHAiOjE1NzUzMzUyMTgsIm5iZiI6MCwiaWF0IjoxNTc1MzA2NDE4LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiJjM2Y0YWYxMS1hMjVlLTQ2YjEtOGJhNi1kOGZkNjMwZmY0NzUiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiIwZWE3MTk0Ni0zMTJjLTRkZWMtYWVmNy0wZDg3Y2RlMjhkMjAiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTMyNyIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTMyNyJ9.MAJ51DolWrUMvUnj--WHphxn2wBowK2ZA_g2hEM5iMXj7Jxwk3wz3BJmdzp3VLDypqTWApf4uG6Ay167CitWVkuwZdZawna8W3LeyZ-VUvaoHYeyg0Htxtl7fI30tozcNbkH59ZQHX9uE_v0gxnM3kOo17BGqum0oe3z6W5CDtTrCvj1FRPssoHiERYnSL3e1Nv_QyVRJzPGd3iQ-ysELBYFOOaPSCxMsQFopbtALTCz_MqQk20FFY0o1Q9b9gnKrZkG4DWtijZ_9dqaL7jLU8VYazUFhD5lpkqxnLY-X9T5FaBKtTyowjVyoI8oErdzKwb4RPgNEeEksAD-dTF7GA')
// sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001327')
// sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

// FOR TESTING ONLY!!!
// eslint-disable-next-line
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiJhYjg5ZjYwZi1lNzkyLTQzNDktYTVlYy1lN2Y3NzBjM2ZkZDIiLCJleHAiOjE1NzUzNDE1NTcsIm5iZiI6MCwiaWF0IjoxNTc1MzEyNzU3LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiI4ZTVkZDYzNS01OGRkLTQ5YzUtYmViMS00NmE1ZDVhMTYzNWMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI2MzdkOWE5NC0yZjA0LTRjOTQtOTdhMy01NWQxZTFiZDQ0ZmIiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImJjMDAwNzI5MSIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImJjMDAwNzI5MSJ9.Y4UNX4hxuoduAdgfjf3Pv32d_GHppMvIvJzd1V8Bug0XehOx2n6as71yRyN0EkEkxb5WMLl3UYm6k0yDrsxbqWoMsy7QzGqwQpB9qsw8auUBmdBdtBjwOOTh4vwyqi-cw2wiFkFgapMyfTV3gzjtzfctT5VuaHBc-A2dbVWqj3wwt6-IUhUQ4R0d66G1Jf8sLqnzHxGY72Es3K6xV3VTHAXEk5dzL5h0fB-5cX3JKYSZPbLK02SBLblF9wICOpIEqv4WwONN4wILBfIMyEXM-2BV9VeuTeTO5PKvesKdPmj7R8RgO--NplG0ega1n416hFATGJcIdGCU4dvFDAXh0g')
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
