export default {
  isRoleStaff: state => {
    return state.keycloakRoles.includes('staff')
  },

  isRoleEdit: state => {
    return state.authRoles.includes('edit')
  },

  isRoleView: state => {
    return state.authRoles.includes('view')
  },

  isAnnualReportEditable: state => {
    return (state.currentFilingStatus === 'NEW' || state.currentFilingStatus === 'DRAFT')
  },

  reportState: state => {
    switch (state.currentFilingStatus) {
      case 'NEW': return ''
      case 'DRAFT': return 'Draft'
      default: return state.currentFilingStatus
    }
  },

  // get last Change of Directors filing from list of past filings
  lastCODFilingDate: state => {
    let lastCOD = null

    for (let i = 0; i < state.filings.length; i++) {
      let filing = state.filings[i].filing
      let filingDate = filing.header.date.slice(0, 10)
      if (filing.hasOwnProperty('changeOfDirectors')) {
        if (lastCOD === null || filingDate.split('-').join('') > lastCOD.split('-').join('')) {
          lastCOD = filingDate
        }
      }
    }
    return lastCOD
  },

  // get last Change of Address filing from list of past filings
  lastCOAFilingDate: state => {
    let lastCOA = null

    for (let i = 0; i < state.filings.length; i++) {
      let filing = state.filings[i].filing
      let filingDate = filing.header.date.slice(0, 10)
      if (filing.hasOwnProperty('changeOfAddress')) {
        if (lastCOA === null || filingDate.split('-').join('') > lastCOA.split('-').join('')) {
          lastCOA = filingDate
        }
      }
    }
    return lastCOA
  },

  // get last filing (of any type) from list of past filings
  lastFilingDate: state => {
    let lastFilingDate = null

    for (let i = 0; i < state.filings.length; i++) {
      let filing = state.filings[i].filing
      let filingDate = filing.header.date.slice(0, 10)
      if (lastFilingDate === null || filingDate.split('-').join('') > lastFilingDate.split('-').join('')) {
        lastFilingDate = filingDate
      }
    }
    return lastFilingDate
  }
}
