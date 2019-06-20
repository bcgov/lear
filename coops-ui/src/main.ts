import '@babel/polyfill'
import Vue from 'vue'
import './plugins/vuetify'
import App from './App.vue'
import axios from './axios-auth'
import Vuelidate from 'vuelidate'
import Vue2Filters from 'vue2-filters'
import Affix from 'vue-affix'
import router from './router'
import store from './store'
import './registerServiceWorker'

Vue.use(Vuelidate)
Vue.use(Vue2Filters)
Vue.use(Affix)
Vue.config.productionTip = false

// just need a token that can get parsed properly (will be expired but doesn't matter for tests)
sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N' +
  '3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIxYzQ2YjIzOS02ZWY0LTQxYTQtYThmMy05N2M5M2IyNmNlMjAiLCJle' +
  'HAiOjE1NTcxNzMyNTYsIm5iZiI6MCwiaWF0IjoxNTU3MTY5NjU2LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2' +
  'EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJzYmMtYXV0aC13ZWIiLCJzdWIiOiIwMzZlN2I4Ny0zZTQxLTQ2MTMtYjFiYy04NWU5OTA' +
  'xNTgzNzAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJkOGZmYjk4' +
  'OS0zNzRlLTRhYTktODc4OS03YTRkODA1ZjNkOTAiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6O' +
  'DA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl' +
  '0IiwidW1hX2F1dGhvcml6YXRpb24iLCJiYXNpYyJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY' +
  '291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTE5MSJ9.Ou' +
  'JLtzYCnkp5KXSiudGFJY6hTSvdE3KokhkEzqU-icxAzQwZSTYbzZQdGsIScy4-DIWHahIGp9L-e6mYlQSQta2rK2Kte85MxThubyw0096UOtAE' +
  'wnS9VURHXPUm4ZUyI4ECkyLlFywOPxAftNdeSYeJx26GHBCvo6uR9Zv6A3yTlJy3B1HJxBWk_6xTAzGPPDCLoyKGeIxGidGujKCKCAfXRMrjhX' +
  'yBv90XzDgZ-To-6_jMjSjBX6Dtq7icdZYLWWDdrhjCpJA5CKS0PlSgeH1Yq4rHd8Ztp5cvVdJFxt87gIopIOQvcy4ji0gtaovgUhiyg07gXGl8' +
  'dGZwn1tpLA')

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
