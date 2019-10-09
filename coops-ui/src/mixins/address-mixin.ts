import { Component, Vue } from 'vue-property-decorator'
import isEqual from 'lodash.isequal'

/**
 * Mixin that provides some useful address utilities.
 */
@Component
export default class AddressMixin extends Vue {
  /**
   * Compares two address objects and returns a boolean indicating
   * if they match.
   *
   * @param addressA An address object.
   * @param addressB An address object.
   * @return boolean True if they match, false if they do not.
   */
  isSameAddress (addressA: Object, addressB: Object): boolean {
    return isEqual(addressA, addressB)
  }
}
