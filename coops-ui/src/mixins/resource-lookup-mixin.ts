import { Component, Vue } from 'vue-property-decorator'
import { mapState } from 'vuex'

/**
 * Mixin for components to retrieve text/settings from json resource.
 */
@Component({
  computed: {
    ...mapState(['configObject'])
  }
})

export default class ResourceLookupMixin extends Vue {
    readonly configObject

    /**
     * Method to return certify message using the configuration lookup object.
     *
     * @param entity The entity type of the component.
     * @return the appropriate message for the certify component for the current filing flow.
     */
    certifyText (feeCode: string): string {
      if (this.configObject && this.configObject.flows) {
        const flow = this.configObject.flows.find(x => x.feeCode === feeCode)
        if (flow && flow.certifyText) {
          return flow.certifyText
        }
      }
      return ''
    }

    /**
     * Method to return the current entity's full display name.
     *
     * @return the entity display name (if the configuration has been loaded).
     */
    displayName () {
      if (this.configObject && this.configObject.displayName) {
        return this.configObject.displayName
      }
      return ''
    }
}
