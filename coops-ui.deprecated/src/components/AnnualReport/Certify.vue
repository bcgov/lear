<template>
  <v-card flat id="AR-step-4-container">
    <div class="certify-container">
      <div class="certifiedby-container">
        <label>Legal Name</label>
        <div class="value certifiedby">
          <v-text-field
            filled
            persistent-hint
            id="certified-by-textfield"
            label="Enter Legal Name"
            hint="Legal name of current director, officer, or lawyer of the association"
            :value="certifiedBy"
            :rules="[ v => !!v || 'Legal Name is required.']"
            @input="emitCertifiedBy($event)"
          />
        </div>
      </div>
      <v-checkbox
        :value="isCertified"
        @change="emitIsCertified($event)"
      >
        <template slot="label">
          <div class="certify-stmt">
            I, <b>{{trimmedCertifiedBy || '[Legal Name]'}}</b>, certify that I have relevant knowledge of the
            {{entityDisplay || 'association'}} and that I am authorized to make this filing.
          </div>
        </template>
      </v-checkbox>
      <p class="certify-clause">Date: {{currentDate}}</p>
      <p class="certify-clause">{{message}}</p>
    </div>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import { mapState } from 'vuex'

@Component({
  computed: {
    ...mapState(['currentDate'])
  }
})
export default class Certify extends Vue {
  readonly currentDate!: string

  // Props passed into this component.
  @Prop({ default: '' })
  private certifiedBy: string

  @Prop({ default: false })
  private isCertified: boolean

  @Prop({ default: '' })
  private message: string

  @Prop({ default: '' })
  private entityDisplay: string

  /**
   * Lifecycle callback to always give the parent a "valid" event for its property values.
   */
  private created (): void {
    this.emitValid(Boolean(this.trimmedCertifiedBy && this.isCertified))
  }

  /**
   * Computed value.
   * @returns The trimmed "Certified By" string (may be '').
   */
  private get trimmedCertifiedBy (): string {
    // remove repeated inline whitespace, and leading/trailing whitespace
    return this.certifiedBy && this.certifiedBy.replace(/\s+/g, ' ').trim()
  }

  // Emit an update event when input changes.
  @Emit('update:certifiedBy')
  private emitCertifiedBy (certifiedBy: string): string {
    // remove repeated inline whitespace, and leading/trailing whitespace
    certifiedBy = certifiedBy && certifiedBy.replace(/\s+/g, ' ').trim()
    this.emitValid(Boolean(certifiedBy && this.isCertified))
    return certifiedBy
  }

  // Emit an update event when checkbox changes.
  @Emit('update:isCertified')
  private emitIsCertified (isCertified: boolean): boolean {
    this.emitValid(Boolean(this.trimmedCertifiedBy && isCertified))
    return isCertified
  }

  // Emit an event indicating whether or not the form is valid.
  @Emit('valid')
  private emitValid (valid: boolean): void { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';

#AR-step-4-container {
  margin-top: 1rem;
  padding-bottom: 0.5rem;
  padding-top: 1rem;
  line-height: 1.2rem;
  font-size: 0.875rem;
}

.certify-container {
  padding: 1.25rem;
}

.certifiedby-container {
  display: flex;
  flex-flow: column nowrap;
  position: relative;

  > label:first-child {
    font-weight: 500;
  }
}

@media (min-width: 768px) {
  .certifiedby-container {
    flex-flow: row nowrap;

    > label:first-child {
      flex: 0 0 auto;
      padding-right: 2rem;
      width: 12rem;
      font-weight: 700;
    }
  }
}

.value.certifiedby {
  min-width: 35rem;
}

.certify-clause {
  padding-left: 2rem;
  color: black;
  font-size: 0.875rem;
}

.certify-stmt {
  display: inline;
  font-size: 0.875rem;
  color: black;
}
</style>
