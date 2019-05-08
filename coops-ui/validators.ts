export function test (value) {
  return value
}

<<<<<<< HEAD
export function isValidYear (date) {
  console.log('validating year: ', date)
  if (!date || date === '' || date.substring(0, 4) === this.year) {
    return true
  }
  return false
}

export function isValidMonth (date) {
  console.log('validating month: ', date)
  if (!date || date === '' || (+date.substring(5, 7) !== 0 && +date.substring(5, 7) <= +this.maxDate.substring(5, 7))) {
    return true
  }
  return false
}

export function isValidDay (date) {
  console.log('validating Day: ', date)

  var day = (new Date(date)).getUTCDate()
  if (!date || date === '' ||
    (+date.substring(8, 10) === day &&
      +date.substring(8, 10) !== 0 &&
      +date.substring(8, 10) <= +this.maxDate.substring(8, 10)
    )) {
    return true
  }
=======
export function agmDate (value) {
  if (value !== '') return true
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
  return false
}

export function isISOFormat (value) {
<<<<<<< HEAD
  console.log('validating isoformat: ', value)
  if (value === '' || !value) return true
  if (value.length === 10 && value.indexOf('/') === 4 && value.indexOf('/', 5) === 7 && value.indexOf('/', 8) === -1) {
=======
  if (value.length === 10 && value.IndexOf('-') === 4 && value.IndexOf('-', 5) === 7 && value.indexOf('-', 8) === -1) {
>>>>>>> Merge branch '237-annual-report-ui' of https://github.com/kialj876/lear into CORS_TEST
    return true
  }
  return false
}
