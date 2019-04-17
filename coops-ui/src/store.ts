import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    userToken: null,
    paymentToken: null,
    corpNum: null,
    ARFilingYear: null,

    currentDate: '',
    filedDate: null,
    agmDate: null,
    noAGM: false,
    validated: false
  },
  mutations: {
  },
  actions: {
  },
  getters: {
  }
})
