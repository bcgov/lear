import { Component, Vue } from 'vue-property-decorator'
import Vue2Filters from 'vue2-filters'

/**
 * Mixin that allows TS inheritance of specified external mixins.
 * @link https://github.com/vuejs/vue-class-component#using-mixins
 */
@Component
export default class ExternalMixin extends Vue {
  limitBy (arr: any, n: number, offset: number): any {
    return Vue2Filters.mixin.methods.limitBy(arr, n, offset)
  }
  filterBy (arr: any[], search: string | number, ...args: any[]): any[] {
    return Vue2Filters.mixin.methods.filterBy(arr, search, ...args)
  }
  orderBy (arr, sortKey, order): any {
    return Vue2Filters.mixin.methods.orderBy(arr, sortKey, order)
  }
  find (arr: any[], search: string | number, ...args: any[]): any {
    return Vue2Filters.mixin.methods.find(arr, search, ...args)
  }
}
