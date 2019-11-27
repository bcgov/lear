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
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIyZWM4YTgzMy05MTBjLTQ4NjUtOGEwNS1iZWEzNzY2ZDFiZTciLCJleHAiOjE1NzQ4OTk0NTcsIm5iZiI6MCwiaWF0IjoxNTc0ODcwNjU3LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiI4ZTVkZDYzNS01OGRkLTQ5YzUtYmViMS00NmE1ZDVhMTYzNWMiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJkNDIxMzk5Zi0zNjcyLTQzNjgtOTE0Mi1hMzE3YzhlMGY2MTgiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImJjMDAwNzI5MSIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImJjMDAwNzI5MSJ9.U1F_cYWiRnOyV9yETGDXH5yHgsq9go_0sPOVGwdBXVs-IKyuPRGhNgOZcpY3Bkzx3pOTTnADPZiF31Lx5CupsGHLQGIC0_DsDekulfL-VJvMm9_YG0oUs06l12hS3zMsNZPCd8SmUVLbypYomkPzn-nSwknyHGhGu9NMEBHL4NQB0G2TRi8ZkwTlo-iPxsgC5dtBGjPXbiZ0Gv-SGLu-shgxrsx__qpw02P9x_Kz6CfgaymrTpkXK7ZeS78zooAyRU6x8tGA9SSzKSgE037-wKlliykLPSKt1Unz-8OyNmrvEtCSNnUcPa_U_aOaYVJsbAqsROq6vAxug6EsUTtzSw')
sessionStorage.setItem('BUSINESS_IDENTIFIER', 'BC0007291')
sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

// // FOR TESTING ONLY!!!
// eslint-disable-next-line
// sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI3MjdlNzdlOS0xMmQ0LTQzMjMtYjVmMy1kMzk4MzZlNDMyOWYiLCJleHAiOjE1NzQ4OTk1MjcsIm5iZiI6MCwiaWF0IjoxNTc0ODcwNzI3LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOlsic2JjLWF1dGgtd2ViIiwiYWNjb3VudCJdLCJzdWIiOiJjM2Y0YWYxMS1hMjVlLTQ2YjEtOGJhNi1kOGZkNjMwZmY0NzUiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI4M2Q1YTdmOC1lN2I4LTQ4MjktYTQ5Ni0xMmEwMjZmODA3NGIiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiIiLCJyb2xlcyI6WyJlZGl0Iiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsImJhc2ljIl0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTMyNyIsImxvZ2luU291cmNlIjoiUEFTU0NPREUiLCJ1c2VybmFtZSI6ImNwMDAwMTMyNyJ9.fJ1YQ4TpgcRfqR_u-NieDh5NDdwCozA6hfiipIytk-lpb_uRcMoeETvjbLdH8lHo7yaG8bNlIEk4yvZAmkZN2uSrXQUkI4sSmlMLug6xzDUmekwGvN0boGLVyoKr-7hn9b1MCuTDL5_q_It4uGfx1JnDkO9TYI6ymf1ymg0kM11iSlgyOM6Tr0ByrIVX6D0yU-9_Yd58QRlb1aoy1myJPCe2Wenv1REvB8FFD1XQtPHVjdW1CLGM3a9KTIzglD-sb1JYx5DagtWqdJGYlsjdcQfxr0-Eey4bhTNGLkH57W3Fh3hQ0qRsV2Sevf5QVhr-CL1thKLFIhlBLrpzyt8vyQ')
// sessionStorage.setItem('BUSINESS_IDENTIFIER', 'CP0001327')
// sessionStorage.setItem('USER_FULL_NAME', 'Cameron Bowler')

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
