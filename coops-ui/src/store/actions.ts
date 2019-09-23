export default {
  setKeycloakRoles ({ commit }, keycloakRoles) {
    commit('keycloakRoles', keycloakRoles)
  },
  setAuthRoles ({ commit }, authRoles) {
    commit('authRoles', authRoles)
  },
  setCurrentDate ({ commit }, currentDate) {
    commit('currentDate', currentDate)
  },
  setLastAgmDate ({ commit }, lastAgmDate) {
    commit('lastAgmDate', lastAgmDate)
  },
  setNextARDate ({ commit }, nextARDate) {
    commit('nextARDate', nextARDate)
  },
  setARFilingYear ({ commit }, ARFilingYear) {
    commit('ARFilingYear', ARFilingYear)
  },
  setEntityBusinessNo ({ commit }, entityBusinessNo) {
    commit('entityBusinessNo', entityBusinessNo)
  },
  setEntityName ({ commit }, entityName) {
    commit('entityName', entityName)
  },
  setEntityType ({ commit }, entityType) {
    commit('entityType', entityType)
  },
  setEntityStatus ({ commit }, entityStatus) {
    commit('entityStatus', entityStatus)
  },
  setEntityIncNo ({ commit }, entityIncNo) {
    commit('entityIncNo', entityIncNo)
  },
  setEntityFoundingDate ({ commit }, entityFoundingDate) {
    commit('entityFoundingDate', entityFoundingDate)
  },
  setBusinessEmail ({ commit }, businessEmail) {
    commit('businessEmail', businessEmail)
  },
  setBusinessPhone ({ commit }, businessPhone) {
    commit('businessPhone', businessPhone)
  },
  setBusinessPhoneExtension ({ commit }, businessPhoneExtension) {
    commit('businessPhoneExtension', businessPhoneExtension)
  },
  setLastPreLoadFilingDate ({ commit }, lastPreLoadFilingDate) {
    commit('lastPreLoadFilingDate', lastPreLoadFilingDate)
  },
  setCurrentFilingStatus ({ commit }, currentFilingStatus) {
    commit('currentFilingStatus', currentFilingStatus)
  },
  setTasks ({ commit }, tasks) {
    commit('tasks', tasks)
  },
  setFilings ({ commit }, filings) {
    commit('filings', filings)
  },
  setMailingAddress ({ commit }, mailingAddress) {
    commit('mailingAddress', mailingAddress)
  },
  setDeliveryAddress ({ commit }, deliveryAddress) {
    commit('deliveryAddress', deliveryAddress)
  },
  setDirectors ({ commit }, directors) {
    commit('directors', directors)
  }
}
