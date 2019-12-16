export default {
  // tombstone data
  keycloakRoles: [] as Array<string>,
  authRoles: [] as Array<string>,
  username: null as string,
  currentDate: null as string,

  // entity info
  entityName: null as string,
  entityType: null as string,
  entityStatus: null as string,
  entityBusinessNo: null as string,
  entityIncNo: null as string,
  lastPreLoadFilingDate: null as string,
  entityFoundingDate: null as string,
  businessEmail: null as string,
  businessPhone: null as string,
  lastAnnualReportDate: null as string,
  businessPhoneExtension: null as string,
  lastAgmDate: null as string,
  nextARDate: null as string,

  ARFilingYear: null as number,
  tasks: [] as Array<object>,
  filings: [] as Array<object>,
  registeredAddress: null as object,
  recordsAddress: null as object,
  directors: [] as Array<object>,

  triggerDashboardReload: false as boolean,

  currentFilingStatus: null as string,
  configObject: null as object
}
