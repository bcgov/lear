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
    regOffAddrChange: false,
    validated: false,

    DeliveryAddressStreet: null,
    DeliveryAddressStreetAdditional: null,
    DeliveryAddressCity: null,
    DeliveryAddressRegion: null,
    DeliveryAddressPostalCode: null,
    DeliveryAddressCountry: null,
    DeliveryAddressInstructions: null,

    MailingAddressStreet: null,
    MailingAddressStreetAdditional: null,
    MailingAddressCity: null,
    MailingAddressRegion: null,
    MailingAddressPostalCode: null,
    MailingAddressCountry: null,
    MailingAddressInstructions: null

  },
  mutations: {
  },
  actions: {
  },
  getters: {
  }
})
