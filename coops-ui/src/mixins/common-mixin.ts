import { Component, Vue } from 'vue-property-decorator'
import omit from 'lodash.omit'

/**
 * Mixin that provides some useful common utilities.
 */
@Component({})
export default class CommonMixin extends Vue {
  /**
   * Removes the specified property from an object
   *
   * @param baseObj The base object
   * @param prop The property to be removed
   */
  omitProp (baseObj: Object, prop: Array<string>): Object {
    return omit(baseObj, prop)
  }
}
