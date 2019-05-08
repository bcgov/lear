import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
<<<<<<< HEAD
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
=======
    userToken: null,
    paymentToken: null,
    corpNum: null,
    ARFilingYear: null,

>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
    validated: false
  },
  mutations: {
  },
  actions: {
  },
  getters: {
  }
})
