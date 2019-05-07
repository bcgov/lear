export function test (value) {
  return value
}

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
  return false
}

export function isISOFormat (value) {
  console.log('validating isoformat: ', value)
  if (value === '' || !value) return true
  if (value.length === 10 && value.indexOf('/') === 4 && value.indexOf('/', 5) === 7 && value.indexOf('/', 8) === -1) {
    return true
  }
  return false
}
