<template>
  <v-card flat id="AR-step-4-container">
    <div class="container">
      <div class="certifiedby-container">
        <label>
          <span>Legal Name</span>
        </label>
        <div class="value certifiedby">
          <v-text-field
            box
            id="certified-by-textfield"
            label="Name of current director, officer, or lawyer of the association"
            :value="certifiedBy"
            @input="emitCertifiedBy"
          />
        </div>
      </div>
      <v-checkbox
        :value="isCertified"
        @change="emitIsCertified"
      >
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

import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component
export default class Certify extends Vue {
  // Props passed into this component.
  @Prop({ default: '' })
  private certifiedBy: string

  @Prop({ default: false })
  private isCertified: boolean

  @Prop({ default: '' })
  private currentDate: string

  /**
   * Lifecycle callback to always give the parent a "valid" event for its property values.
   */
  private created (): void {
    this.emitValid(this.trimmedCertifiedBy && this.isCertified)
  }

  /**
   * Computed value.
   * @return The trimmed "Certified By" string (may be '').
   */
  private get trimmedCertifiedBy (): string {
    return this.certifiedBy && this.certifiedBy.trim()
  }

  // Emit an update event.
  @Emit('update:certifiedBy')
  private emitCertifiedBy (val: string): string {
    this.emitValid(val && val.trim() && this.isCertified)

    return val
  }

  // Emit an update event.
  @Emit('update:isCertified')
  private emitIsCertified (val: boolean): boolean {
    this.emitValid(this.trimmedCertifiedBy && !!val)

    return val
  }

  // Emit an event indicating whether or not the form is valid.
  @Emit('valid')
  private emitValid (val: boolean): boolean {
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
