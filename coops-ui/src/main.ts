import '@babel/polyfill'
import Vue from 'vue'
import App from './App.vue'
import axios from './axios-auth'
import Vuelidate from 'vuelidate'
import Vue2Filters from 'vue2-filters'
import Affix from 'vue-affix'
import router from './router'
import store from './store'
import './plugins/vuetify'
import './registerServiceWorker'

Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)
Vue.config.productionTip = false

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
