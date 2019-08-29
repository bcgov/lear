<template>
  <v-card flat id="AR-step-4-container">
    <div class="container">
      <div class="certifiedby-container">
        <label>
          <span>Legal Name</span>
        </label>
        <div class="value certifiedby">
          <v-text-field
            id="certified-by-textfield"
            v-model="certifyTextField"
            label="Name of current director, officer, or lawyer of the association"
            box
          />
        </div>
      </div>
      <v-checkbox v-model="certifyCheckbox">
        <template slot="label">
          <div class="certify-stmt">
            I, <b>{{trimmedCertifiedBy || '[Legal Name]'}}</b>, certify that I have relevant knowledge of the
            association and that I am authorized to make this filing.
          </div>
        </template>
      </v-checkbox>
      <p class="certify-clause">{{currentDate}}</p>
      <p class="certify-clause">
        Note: It is an offence to make a false or misleading statement in
        respect of a material fact in a record submitted to the Corporate Registry for filing.
        See section 200 of the Cooperatives Association Act.
      </p>
    </div>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop, Watch, Emit } from 'vue-property-decorator'
import { mapState } from 'vuex'

@Component({
  computed: {
    // Property definition for runtime environment.
    ...mapState({ currentDate: 'currentDate' })
  }
})
export default class Certify extends Vue {
  // Local definition of computed property for static type checking.
  // Use non-null assertion operator to allow use before assignment.
  readonly currentDate!: string

  // Model properties for the Text Field and Checkbox controls.
  private certifyTextField: string = ''
  private certifyCheckbox: boolean = false

  // Props passed into this component.
  @Prop({ default: '' })
  private certifiedBy: string

  @Prop({ default: false })
  private isCertified: boolean

  /**
   * Computed value.
   * @return The trimmed "Certified By" string (may be '').
   */
  private get trimmedCertifiedBy (): string {
    return this.certifyTextField && this.certifyTextField.trim()
  }

  /**
   * Computed value.
   * @return Whether or not this component (form) is valid.
   */
  private get isCertifyValid (): boolean {
    return !!(this.certifyCheckbox && this.trimmedCertifiedBy)
  }

  // When prop changes, update text field.
  @Watch('certifiedBy')
  private onCertifiedByChanged (val): void {
    this.certifyTextField = val
  }

  // When prop changes, update checkbox.
  @Watch('isCertified')
  private onIsCertifiedChanged (val): void {
    this.certifyCheckbox = val
  }

  // When the trimmed "Certified By" string changes, signal the parent.
  @Watch('trimmedCertifiedBy')
  private ontrimmedCertifiedByChanged (val): void {
    this.emitCertifiedBy(val)
  }

  // When this form's validity changes, signal the parent.
  @Watch('isCertifyValid')
  private onIsCertifyValidChanged (val): void {
    this.emitIsCertified(val)
  }

  // Emit an update event.
  @Emit('update:certifiedBy')
  private emitCertifiedBy (val) {
    return val
  }

  // Emit an update event.
  @Emit('update:isCertified')
  private emitIsCertified (val) {
    return val
  }
}
</script>

<style lang="stylus" scoped>
@import '../../assets/styles/theme.styl'

.certifiedby-container
  display flex
  flex-flow column nowrap
  position relative
  > label:first-child
    font-weight 500

@media (min-width 768px)
  .certifiedby-container
    flex-flow row nowrap
    > label:first-child
      flex 0 0 auto
      padding-right: 2rem
      width 12rem

.value.certifiedby
  min-width 35rem

.certify-clause
  padding-left 2rem
  color black
  font-size 0.875rem

.certify-stmt
  display:inline
  font-size: 0.875rem
  color black

#AR-step-4-container
  margin-top: 1rem;
  padding-bottom: 0.5rem;
  padding-top: 1rem;
  line-height: 1.2rem;
  font-size: 0.875rem;
</style>
