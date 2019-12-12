import { Component, Vue } from 'vue-property-decorator'
import { mapState } from 'vuex'

/**
 * Mixin that provides an entity filter utility.
 */
@Component({
  computed: {
    ...mapState(['configObject'])
  }
})

export default class ResourceLookupMixin extends Vue {
    readonly configObject

    /**
     * Method to compare the conditional entity to the entityType defined from the Store.
     *
     * @param entity The entity type of the component.
     * @return boolean A boolean indicating if the entityType given matches the entityType assigned to the component.
     */
    certifyText (feeCode: string): string {
      if (this.configObject && this.configObject.flows) {
        const flow = this.configObject.flows.find(x => x.feeCode === feeCode)
        return flow.certifyText
      }
      return ''
    }

    displayName () {
      if (this.configObject && this.configObject.displayName) {
        return this.configObject.displayName
      }
      return ''
    }
}
