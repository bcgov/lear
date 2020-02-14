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
  nextARDate (state, nextARDate) {
    state.nextARDate = nextARDate
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
  entityType (state, entityType) {
    state.entityType = entityType
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
  registeredAddress (state, registeredAddress) {
    state.registeredAddress = registeredAddress
  },
  recordsAddress (state, recordsAddress) {
    state.recordsAddress = recordsAddress
  },
  directors (state, directors) {
    state.directors = directors
  },
  triggerDashboardReload (state, value) {
    state.triggerDashboardReload = value
  },
  lastAnnualReportDate (state, value) {
    state.lastAnnualReportDate = value
  },
  configObject (state, value) {
    state.configObject = value
  }
}
