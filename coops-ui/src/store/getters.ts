export default {
  isAnnualReportEditable: state => {
    return (state.currentARStatus === 'TODO' || state.currentARStatus === 'DRAFT')
  },
  reportState: state => {
    if (state.currentARStatus === 'TODO' || state.currentARStatus === 'DRAFT') {
      return 'Draft'
    } else {
      return state.currentARStatus
    }
  }
}
