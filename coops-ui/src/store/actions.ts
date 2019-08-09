export default {
  setCorpNum ({ commit }, corpNum) {
    commit('corpNum', corpNum)
  },
  setCurrentDate ({ commit }, currentDate) {
    commit('currentDate', currentDate)
  },
  setLastAgmDate ({ commit }, lastAgmDate) {
    commit('lastAgmDate', lastAgmDate)
  },
  setARFilingYear ({ commit }, ARFilingYear) {
    commit('ARFilingYear', ARFilingYear)
  },
  setFiledDate ({ commit }, filedDate) {
    commit('filedDate', filedDate)
  },
  setAgmDate ({ commit }, agmDate) {
    commit('agmDate', agmDate)
  },
  setNoAGM ({ commit }, noAGM) {
    commit('noAGM', noAGM)
  },
  setRegOffAddrChange ({ commit }, regOffAddrChange) {
    commit('regOffAddrChange', regOffAddrChange)
  },
  setValidated ({ commit }, validated) {
    commit('validated', validated)
  },
  setEntityBusinessNo ({ commit }, entityBusinessNo) {
    commit('entityBusinessNo', entityBusinessNo)
  },
  setEntityName ({ commit }, entityName) {
    commit('entityName', entityName)
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
  setLastPreLoadFilingDate ({ commit }, lastPreLoadFilingDate) {
    commit('lastPreLoadFilingDate', lastPreLoadFilingDate)
  },
  setCurrentFilingStatus ({ commit }, currentFilingStatus) {
    commit('currentFilingStatus', currentFilingStatus)
  },
  setAddressesFormValid ({ commit }, addressesFormValid) {
    commit('addressesFormValid', addressesFormValid)
  },
  setDirectorFormValid ({ commit }, directorFormValid) {
    commit('directorFormValid', directorFormValid)
  },
  setAgmDateValid ({ commit }, agmDateValid) {
    commit('agmDateValid', agmDateValid)
  },
  setFilingHistory ({ commit }, filingHistory) {
    commit('filingHistory', filingHistory)
  }
}
