// import '@babel/polyfill'
import 'core-js/stable'
import 'regenerator-runtime/runtime'
import Vue from 'vue'
import Vue2Filters from 'vue2-filters'
import Affix from 'vue-affix'
import '@/plugins/vuetify'
import '@/plugins/vuelidate'
import '@/registerServiceWorker'
import App from '@/App.vue'
import router from '@/router'
import store from '@/store/store'

Vue.use(Vue2Filters)
Vue.use(Affix)
Vue.config.productionTip = false

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
