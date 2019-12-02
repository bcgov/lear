export function isNotNull (date: string): boolean {
  return !!date
}

export function isValidFormat (date: string, separator: string): boolean {
  if (!date) return false
  // special handling because Vuelidate doesn't pass in separator
  separator = (typeof separator === 'string') ? separator : '/'
  const validLen = (date.length === 10)
  const firstSlash = (date.indexOf(separator) === 4)
  const secondSlash = (date.indexOf(separator, 5) === 7)
  const thirdSlash = (date.indexOf(separator, 8) === -1)
  return (validLen && firstSlash && secondSlash && thirdSlash)
}

export function isValidYear (date: string): boolean {
  if (!date) return false
  const year = +date.substring(0, 4)
  return (year === this.ARFilingYear)
}

export function isValidMonth (date: string): boolean {
  if (!date) return false
  const month = +date.substring(5, 7)
  const min = +this.minDate.substring(5, 7)
  const max = +this.maxDate.substring(5, 7)
  return (month >= min && month <= max)
}

export function isValidDay (date: string): boolean {
  if (!date) return false
  // first make sure date has valid year/month/day values
  const year = +date.substring(0, 4)
  const month = +date.substring(5, 7)
  const day = +date.substring(8, 10)
  const jsd = new Date(date)
  if (year !== jsd.getUTCFullYear() ||
    month !== jsd.getUTCMonth() + 1 ||
    day !== jsd.getUTCDate()) return false
  // now make sure date is between min and max
  const time = new Date(date.split('/').join('-')).getTime()
  const min = new Date(this.minDate).getTime()
  const max = new Date(this.maxDate).getTime()
  return (time >= min && time <= max)
}

export function isValidCODDate (dateInput: string, separator: string): boolean {
  separator = (typeof separator === 'string') ? separator : '/'

  if (!dateInput) return false

  var d1 = this.minDate == null ? 0 : this.minDate.split('-').join('')
  var d2 = this.maxDate.split('-').join('')
  var c = dateInput.split(separator).join('')
  return c >= d1 && c <= d2
}
