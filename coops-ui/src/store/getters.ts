export default {
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
  lastCODFilingDate: state => {
    // get last Change of Directors filing from list of past filings
    let lastCOD = null

    for (let i = 0; i < state.filingHistory.length; i++) {
      let filing = state.filingHistory[i].filing
      if (filing.hasOwnProperty('changeOfDirectors')) {
        lastCOD = lastCOD === null || filing.header.date.split('-').join('') > lastCOD.split('-').join('')
          ? filing.header.date : lastCOD
      }
    }
    return lastCOD
  },
  lastFilingDate: state => {
    // get last filing (of any type) from list of past filings
    let lastFilingDate = null

    for (let i = 0; i < state.filingHistory.length; i++) {
      let filing = state.filingHistory[i].filing
      if (lastFilingDate === null || filing.header.date.split('-').join('') > lastFilingDate.split('-').join('')) {
        lastFilingDate = filing.header.date
      }
    }
    return lastFilingDate
  }
}
