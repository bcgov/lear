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
  }
}
