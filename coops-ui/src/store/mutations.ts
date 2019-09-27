export default {
  keycloakRoles (state, keycloakRoles) {
    state.keycloakRoles = keycloakRoles
  },
  authRoles (state, authRoles) {
    state.authRoles = authRoles
  },
  currentDate (state, currentDate) {
    state.currentDate = currentDate
  },
  lastAgmDate (state, lastAgmDate) {
    state.lastAgmDate = lastAgmDate
  },
  ARFilingYear (state, ARFilingYear) {
    state.ARFilingYear = ARFilingYear
  },
  entityBusinessNo (state, entityBusinessNo) {
    state.entityBusinessNo = entityBusinessNo
  },
  entityName (state, entityName) {
    state.entityName = entityName
  },
  entityStatus (state, entityStatus) {
    state.entityStatus = entityStatus
  },
  entityIncNo (state, entityIncNo) {
    state.entityIncNo = entityIncNo
  },
  entityFoundingDate (state, entityFoundingDate) {
    state.entityFoundingDate = entityFoundingDate
  },
  businessEmail (state, businessEmail) {
    state.businessEmail = businessEmail
  },
  businessPhone (state, businessPhone) {
    state.businessPhone = businessPhone
  },
  businessPhoneExtension (state, businessPhoneExtension) {
    state.businessPhoneExtension = businessPhoneExtension
  },
  lastPreLoadFilingDate (state, lastPreLoadFilingDate) {
    state.lastPreLoadFilingDate = lastPreLoadFilingDate
  },
  currentFilingStatus (state, currentFilingStatus) {
    state.currentFilingStatus = currentFilingStatus
  },
  tasks (state, tasks) {
    state.tasks = tasks
  },
  filings (state, filings) {
    state.filings = filings
  },
  mailingAddress (state, mailingAddress) {
    state.mailingAddress = mailingAddress
  },
  deliveryAddress (state, deliveryAddress) {
    state.deliveryAddress = deliveryAddress
  },
  directors (state, directors) {
    state.directors = directors
  },
  triggerDashboardReload (state, value) {
    state.triggerDashboardReload = value
  }
}
