import '@babel/polyfill'
import Vue from 'vue'
import '@/plugins/vuetify'
import App from '@/App.vue'
import Vuelidate from 'vuelidate'
import Vue2Filters from 'vue2-filters'
import Affix from 'vue-affix'
import router from '@/router'
import store from '@/store/store'
import '@/registerServiceWorker'

Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)
Vue.config.productionTip = false

// token for temporary development use (will be expired but doesn't matter for tests)
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbW' +
  'dtZUk0MnVsdUZ0N3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiI4MTQzZGZmNi04ZmRkLTQwOGQ' +
  'tODJiZC02NDQ0ZDcyYTE1ZGIiLCJleHAiOjE1NjI0MzUwMDgsIm5iZiI6MCwiaWF0IjoxNTYyMzQ4NjA4LCJpc3MiOiJo' +
  'dHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJzYmMtY' +
  'XV0aC13ZWIiLCJzdWIiOiJhMGQxNjhiNy01NTg2LTQwNjMtYjk4ZC1lYzRkZTgzYmNkYmQiLCJ0eXAiOiJCZWFyZXIiLC' +
  'JhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiIwNTFiZTMwZi0zNmNlLTRmYzk' +
  'tYmUzZi04MjZjYzdhZmRhNGQiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6' +
  'ODA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6e' +
  'yJyb2xlcyI6WyJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOl' +
  'sibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInByZWZlcnJlZF9' +
  '1c2VybmFtZSI6ImNwMDAwMjA5OCJ9.PaTNq2GJ-Y9UB4G5euQLnGsWCBRNAq705GuRSWm2QSHZ2npphk-tAmySf5KfIMe' +
  'M5I5riVBrh9lQR-3RVjB3hkNfi_WiwB1wdj7cY1Bd4E164lXUiZRrMw-PqbDTwoJf6o_QAK89xnXNQaW26apTGIUFH1ob' +
  'nPdrezyaIzxj8d2OLUAVMJ1BbRRmeppJ2tkJi72mkXx6xl5x1NvDQtr3Hr4Zp62SBKzFYkbvnpUkE06CLYhI_NPBjV1VO' +
  'eRvNjJLVhN7mvgIvISABpKeb3iBT2-J_paSAJZoHHheV5e1DkHi8SRZSp-tGFza-E_RrDrcrJUoHaCVO_2fzb-zM9zXow')

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
