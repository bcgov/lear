export function test (value) {
  return value
}

export function agmDate (value) {
  if (value !== '') return true
  return false
}

export function isISOFormat (value) {
  if (value.length === 10 && value.IndexOf('-') === 4 && value.IndexOf('-', 5) === 7 && value.indexOf('-', 8) === -1) {
    return true
  }
  return false
}
