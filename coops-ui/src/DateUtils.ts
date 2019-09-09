import Vue from 'vue'

const DateUtils = Vue.extend({
  methods: {
    /**
     * Converts a JavaScript date object to a simple date string (YYYY-MM-DD).
     * @param date The date to convert.
     */
    dateToUsableString: function (date: Date): string {
      if (!date || date.toString() === 'Invalid Date') return null

      const yyyy = date.getFullYear().toString()
      const mm = (date.getMonth() + 1).toString().padStart(2, '0')
      const dd = date.getDate().toString().padStart(2, '0')
      return `${yyyy}-${mm}-${dd}`
    },

    /**
     * Converts a number (YYYYMMDD) to a simple date string (YYYY-MM-DD).
     * @param n The number to convert.
     */
    numToUsableString: function (val: number | string): string {
      if (!val || val.toString().length !== 8) return null

      val = val.toString()

      const yyyy = val.substr(0, 4)
      const mm = val.substr(4, 2)
      const dd = val.substr(6, 2)
      return `${yyyy}-${mm}-${dd}`
    },

    /**
     * Compare simple date strings (YYYY-MM-DD)..
     * @param date1 The first date to compare.
     * @param date2 The second date to compare.
     * @param operator The operator to use for comparison.
     */
    compareDates (date1: string, date2: string, operator: string): boolean {
      if (!date1 || !date2 || !operator) return true

      // convert dates to numbers YYYYMMDD
      date1 = date1.split('-').join('')
      date2 = date2.split('-').join('')

      return eval(date1 + operator + date2) // eslint-disable-line no-eval
    }
  }
})

export default DateUtils
