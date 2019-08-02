export function isNotNull (date: string): boolean {
  return !!date
}

export function isValidYear (date: string): boolean {
  if (!date || date === '') return true
  const year = +date.substring(0, 4)
  return (year === this.ARFilingYear)
}

export function isValidMonth (date: string): boolean {
  if (!date || date === '') return true
  const month = +date.substring(5, 7)
  const max = +this.maxDate.substring(5, 7)
  return (month > 0 && month <= max)
}

export function isValidDay (date: string): boolean {
  if (!date || date === '') return true
  const day = +date.substring(8, 10)
  // use getUTCDate() to ignore local time (we only care about date part)
  const today = (new Date(date)).getUTCDate()
  const date1 = date.split('/').join('')
  const date2 = this.maxDate.split('-').join('')
  return (day === today && day > 0 && date1 <= date2)
}

export function isISOFormat (date: string): boolean {
  if (!date || date === '') return true
  const validLen = (date.length === 10)
  const firstSlash = (date.indexOf('/') === 4)
  const secondSlash = (date.indexOf('/', 5) === 7)
  const thirdSlash = (date.indexOf('/', 8) === -1)
  return (validLen && firstSlash && secondSlash && thirdSlash)
}
