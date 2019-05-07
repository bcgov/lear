import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    corpNum: null,
    currentDate: '',

    entityName: null,
    entityStatus: null,
    entityBusinessNo: null,
    entityIncNo: null,

    ARFilingYear: null,
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
