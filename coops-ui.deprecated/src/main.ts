import 'core-js/stable' // to polyfill ECMAScript features
import 'regenerator-runtime/runtime' // to use transpiled generator functions
import '@mdi/font/css/materialdesignicons.min.css' // ensure you are using css-loader
import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import Vuelidate from 'vuelidate'
import Affix from 'vue-affix'
import Vue2Filters from 'vue2-filters' // needed by SbcFeeSummary
import configHelper from '@/utils/config-helper'
import router from '@/router'
import store from '@/store/store'
import { withFlagProvider } from 'ld-vue'
import '@/registerServiceWorker'
import '@/assets/styles/base.scss'
import '@/assets/styles/layout.scss'
import '@/assets/styles/overrides.scss'
import TokenServices from 'sbc-common-components/src/services/token.services'
import App from '@/App.vue'

// get rid of "You are running Vue in development mode" console message
Vue.config.productionTip = false

Vue.use(Vuetify)
Vue.use(Vuelidate)
Vue.use(Affix)
Vue.use(Vue2Filters)

const vuetify = new Vuetify({ iconfont: 'mdi' })

/**
 * first fetch config from server, then load Vue
 */
configHelper.fetchConfig()
  .then(() => {
    // ensure we have the necessary Keycloak tokens
    if (!haveKcTokens()) {
      console.info('Redirecting to Signin URL...') // eslint-disable-line no-console
      const signinUrl: string = sessionStorage.getItem('SIGNIN_URL') || ''
      const businessesUrl: string = sessionStorage.getItem('BUSINESSES_URL') || ''
      // assume Signin URL is always reachable
      // append Businesses URL to return to
      signinUrl && businessesUrl && window.location.assign(signinUrl + encodeURIComponent(businessesUrl))
      return // do not execute remaining code
    }

    // start token service to refresh KC token periodically
    console.info('Starting token refresh service...') // eslint-disable-line no-console
    const tokenServices = new TokenServices()
    tokenServices.initUsingUrl(sessionStorage.getItem('KEYCLOAK_CONFIG_URL'))
      .then(() => tokenServices.scheduleRefreshTimer())

    new Vue({
      vuetify,
      router,
      store,
      mixins: [withFlagProvider({ clientSideId: window['ldClientId'] })],
      render: h => h(App)
    }).$mount('#app')
  })
  .catch(error => {
    /**
     * This catches any un-handled errors from fetchConfig()
     * or anything else in then() block above.
     */
    console.error(error) // eslint-disable-line no-console
    alert('There was an error starting this page. (See console for details.)' +
      '\n\n' +
      'Click OK to go to Cooperatives Online.')
    window.location.assign('/cooperatives/auth/') // TODO: update this when new URLs are in place
  })

function haveKcTokens (): boolean {
  return Boolean(sessionStorage.getItem('KEYCLOAK_TOKEN') &&
    sessionStorage.getItem('KEYCLOAK_REFRESH_TOKEN') &&
    sessionStorage.getItem('KEYCLOAK_ID_TOKEN'))
}
