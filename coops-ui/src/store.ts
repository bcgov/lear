import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    userToken: null,
    paymentToken: null,
    corpNum: null,
    ARFilingYear: null,

    validated: false
  },
  mutations: {
  },
  actions: {
  },
  getters: {
  }
})
