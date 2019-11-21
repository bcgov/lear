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

  entityTypeToDisplay (): string {
    switch (this.entityType) {
      case 'CP':
        return 'Cooperative'
      case 'BC':
        return 'Benefits Company'
    }
    return ''
  }

  entityLegalSection (): string {
    switch (this.entityType) {
      case 'CP':
        return 'Cooperative Association Act'
      case 'BC':
        return 'Business Corporations Act'
    }
    return ''
  }

  getCODSectionCode () :string {
    switch (this.entityType) {
      case 'CP':
        return '78'
      case 'BC':
        return '127'
    }
    return ''
  }

  getARSectionCode () :string {
    switch (this.entityType) {
      case 'CP':
        return '126'
      case 'BC':
        return '51'
    }
    return ''
  }

  getCOASectionCode () :string {
    switch (this.entityType) {
      case 'CP':
        return '126'
      case 'BC':
        return '51'
    }
    return ''
  }
}
