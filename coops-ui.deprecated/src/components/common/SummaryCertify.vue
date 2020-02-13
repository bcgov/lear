<template>
  <v-card flat id="certify-container">
    <p class="certify-content">
        I, <b>{{trimmedCertifiedBy || '[Legal Name]'}}</b>, certify that I have relevant knowledge of the
        {{entityDisplay || 'association'}} and that I am authorized to make this filing.
    </p>
    <p class="certify-content">Date: {{currentDate}}</p>
    <p class="certify-content">{{message}}</p>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator'
import { mapState } from 'vuex'

@Component({
  computed: {
    ...mapState(['currentDate'])
  }
})
export default class SummaryCertify extends Vue {
  readonly currentDate!: string

  // Props passed into this component.
  @Prop({ default: '' })
  private certifiedBy: string

   @Prop({ default: '' })
  private message: string

  @Prop({ default: '' })
  private entityDisplay: string

  /**
   * Computed value.
   * @returns The trimmed "Certified By" string (may be '').
   */
  private get trimmedCertifiedBy (): string {
    return this.certifiedBy && this.certifiedBy.trim()
  }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';

#certify-container {
  margin-top: 1rem;
  padding: 1.25rem 1.25rem 0.25rem 1.25rem;
  font-size: 0.875rem;

  .certify-content {
    color: black;
    font-size: 1rem;
    line-height: 1.5rem;
  }
}
</style>
