export default {
  isRoleStaff (state): boolean {
    return state.keycloakRoles.includes('staff')
  },

  isRoleEdit (state): boolean {
    return state.authRoles.includes('edit')
  },

  isRoleView (state): boolean {
    return state.authRoles.includes('view')
  },

  isAnnualReportEditable (state): boolean {
    return (state.currentFilingStatus === 'NEW' || state.currentFilingStatus === 'DRAFT')
  },

  reportState (state): string {
    switch (state.currentFilingStatus) {
      case 'NEW': return ''
      case 'DRAFT': return 'Draft'
      default: return state.currentFilingStatus
    }
  },

  // get last Change of Directors filing from list of past filings
  lastCODFilingDate (state): string {
    let lastCOD: string = null

    for (let i = 0; i < state.filings.length; i++) {
      let filing = state.filings[i].filing
      let filingDate = filing.header.effectiveDate || filing.header.date
      filingDate = filingDate.slice(0, 10)
      if (filing.hasOwnProperty('changeOfDirectors')) {
        if (lastCOD === null || filingDate.split('-').join('') > lastCOD.split('-').join('')) {
          lastCOD = filingDate
        }
      }
    }
    return lastCOD
  },

  // get last Change of Address filing from list of past filings
  lastCOAFilingDate (state): string {
    let lastCOA: string = null

    for (let i = 0; i < state.filings.length; i++) {
      let filing = state.filings[i].filing
      let filingDate = filing.header.effectiveDate || filing.header.date
      filingDate = filingDate.slice(0, 10)
      if (filing.hasOwnProperty('changeOfAddress')) {
        if (lastCOA === null || filingDate.split('-').join('') > lastCOA.split('-').join('')) {
          lastCOA = filingDate
        }
      }
    }
    return lastCOA
  },

  // get last filing (of any type) from list of past filings
  lastFilingDate (state): string {
    let lastFilingDate: string = null

    for (let i = 0; i < state.filings.length; i++) {
      let filing = state.filings[i].filing
      let filingDate = filing.header.effectiveDate || filing.header.date
      filingDate = filingDate.slice(0, 10)
      if (lastFilingDate === null || filingDate.split('-').join('') > lastFilingDate.split('-').join('')) {
        lastFilingDate = filingDate
      }
    }
    return lastFilingDate
  },

  getConfigObject (state): object {
    return null
  }
}
