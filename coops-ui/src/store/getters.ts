export default {
  isAnnualReportEditable: state => {
    return (state.currentARStatus === 'NEW' || state.currentARStatus === 'DRAFT')
  },
  reportState: state => {
    switch (state.currentARStatus) {
      case 'NEW': return ''
      case 'DRAFT': return 'Draft'
      default: return state.currentARStatus
    }
  },
  lastCODFilingDate: state => {
    // get last Change of Directors filing from list of past filings
    let lastCOD = null

    for (let i = 0; i < state.filingHistory.length; i++) {
      let filing = state.filingHistory[i].filing
      console.log('got here ' + i)
      console.log(lastCOD)
      if (filing.hasOwnProperty('changeOfDirectors')) {
        lastCOD = lastCOD === null || filing.header.date.split('-').join('') > lastCOD.split('-').join('')
          ? filing.header.date : lastCOD
        console.log(lastCOD)
      }
    }
    return lastCOD
  }
}
