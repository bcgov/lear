import { Component, Vue } from 'vue-property-decorator'
import { mapState } from 'vuex'
import { AlertMessage } from '@/interfaces'
import { FilingCodes } from '@/enums'
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

    /**
     * Method to validate directors on edit/cease and return any warning messages.
     *
     * @return the compliance message or null (if the configuration has been loaded).
     */
    directorWarning (directors: Array<any>): AlertMessage {
      const configSection = this.configObject.flows.find(x => x.feeCode === FilingCodes.DIRECTOR_CHANGE_OT).warnings
      let errors = []
      // FUTURE: Too much code for this. Can be condensed and made more reusable.
      if (configSection.bcResident) {
        if (directors.filter(x => (x.deliveryAddress.addressRegion !== 'BC' ||
        (x.mailingAddress && x.mailingAddress.addressRegion !== 'BC'))).length === directors.length) {
          errors.push({ 'title': configSection.bcResident.title, 'msg': configSection.bcResident.message })
        }
      }

      if (configSection.canadianResident) {
        if (directors.filter(x => (x.deliveryAddress.addressCountry !== 'CA' ||
        (x.mailingAddress && x.mailingAddress.addressRegion !== 'BC'))).length === directors.length) {
          errors.push({ 'title': configSection.canadianResident.title, 'msg': configSection.canadianResident.message })
        }
      }

      if (configSection.minDirectors) {
        const min = configSection.minDirectors.count
        if (directors.filter(x => x.actions.indexOf('ceased') < 0).length < min) {
          errors.push({ 'title': configSection.minDirectors.title, 'msg': configSection.minDirectors.message })
        }
      }

      if (errors.length > 0) {
        return errors[0]
      }
      return null
    }
}
