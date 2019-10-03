import { Component, Vue } from 'vue-property-decorator'
import { mapState } from 'vuex'

/**
 * Mixin that provides an entity filter utility.
 */
@Component({
  computed: {
    ...mapState(['entityType'])
  }
})
export default class EntityFilterMixin extends Vue {
  readonly entityType: string

  /**
   * Method to compare the conditional entity to the entityType defined from the Store.
   *
   * @param entity The entity type of the component.
   * @return boolean A boolean indicating if the entityType given matches the entityType assigned to the component.
   */
  entityFilter (entityType: string): boolean {
    return this.entityType === entityType
  }
}
