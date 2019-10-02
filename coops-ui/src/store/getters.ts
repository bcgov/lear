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
      if (filing.hasOwnProperty('changeOfDirectors')) {
        if (lastCOD === null || filing.header.date.split('-').join('') > lastCOD.split('-').join('')) {
          lastCOD = filing.header.date
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
      if (filing.hasOwnProperty('changeOfAddress')) {
        if (lastCOA === null || filing.header.date.split('-').join('') > lastCOA.split('-').join('')) {
          lastCOA = filing.header.date
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
      if (lastFilingDate === null || filing.header.date.split('-').join('') > lastFilingDate.split('-').join('')) {
        lastFilingDate = filing.header.date
      }
    }
    return lastFilingDate
  }
}
