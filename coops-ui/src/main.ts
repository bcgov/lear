import '@babel/polyfill'
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'
import Vuelidate from 'vuelidate'
import router from './router'
import store from './store'
import './plugins/vuetify'
import './registerServiceWorker'

Vue.use(Vuelidate)
Vue.config.productionTip = false

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
