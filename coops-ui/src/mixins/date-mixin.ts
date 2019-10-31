import { Component, Vue } from 'vue-property-decorator'

/**
 * Mixin that provides some useful date utilities.
 */
@Component({})
export default class DateMixin extends Vue {
  /**
   * Converts a JavaScript date object to a simple date string.
   * @param date The date to convert.
   * @returns A simple date string formatted as YYYY-MM-DD.
   */
  dateToUsableString (date: Date): string {
    if (!date || date.toString() === 'Invalid Date') return null

    const yyyy = date.getFullYear().toString()
    const mm = (date.getMonth() + 1).toString().padStart(2, '0')
    const dd = date.getDate().toString().padStart(2, '0')
    return `${yyyy}-${mm}-${dd}`
  }

  /**
   * Converts a number (YYYYMMDD) to a simple date string.
   * @param n The number to convert.
   * @returns A simple date string formatted as YYYY-MM-DD.
   */
  numToUsableString (val: number | string): string {
    if (!val || val.toString().length !== 8) return null

    val = val.toString()

    const yyyy = val.substr(0, 4)
    const mm = val.substr(4, 2)
    const dd = val.substr(6, 2)
    return `${yyyy}-${mm}-${dd}`
  }

  /**
   * Compares simple date strings (YYYY-MM-DD).
   * @param date1 The first date to compare.
   * @param date2 The second date to compare.
   * @param operator The operator to use for comparison.
   * @returns The result of the comparison (true or false).
   */
  compareDates (date1: string, date2: string, operator: string): boolean {
    if (!date1 || !date2 || !operator) return true

    // convert dates to numbers YYYYMMDD
    date1 = date1.split('-').join('')
    date2 = date2.split('-').join('')

    return eval(date1 + operator + date2) // eslint-disable-line no-eval
  }

  /**
   * Formats a simple date string (YYYY-MM-DD) to (Month Day, Year) for readability.
   *
   * @param date The date string to format.
   * @returns The re-formatted date string without the day name.
   */
  toReadableDate (date: string): string {
    // Cast to a workable dateString
    // Split into an array.
    let formatDate = (new Date(date).toDateString()).split(' ')

    // Remove the 'weekday' from the array
    // Join the array
    // Add a comma to the date output.
    const regex = / (?!.* )/
    return formatDate.slice(1).join(' ').replace(regex, ', ')
  }
}
