export function test (value) {
  return value
}

export function isValidYear (date: string): boolean {
  console.log('validating year, date =', date)

  if (!date || date === '') return true
  const year = date.substring(0, 4)
  return (year === this.year)
}

export function isValidMonth (date: string): boolean {
  console.log('validating month, date =', date)

  if (!date || date === '') return true
  const month = +date.substring(5, 7)
  const max = +this.maxDate.substring(5, 7)
  return (month > 0 && month <= max)
}

export function isValidDay (date: string): boolean {
  console.log('validating day, date =', date)

  if (!date || date === '') return true
  const day = +date.substring(8, 10)
  const today = (new Date(date)).getUTCDate()
  const max = +this.maxDate.substring(8, 10)
  return (day === today && day > 0 && day <= max)
}

export function isISOFormat (date: string): boolean {
  console.log('validating ISO format, date =', date)

  if (!date || date === '') return true
  const validLen = (date.length === 10)
  const firstSlash = (date.indexOf('/') === 4)
  const secondSlash = (date.indexOf('/', 5) === 7)
  const thirdSlash = (date.indexOf('/', 8) === -1)
  return (validLen && firstSlash && secondSlash && thirdSlash)
}
