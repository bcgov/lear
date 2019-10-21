<template>

  <v-card flat id="certify-container">
    <div class="container">
      <p class="certify-content">I, <b>{{ trimmedCertifiedBy || '[Legal Name]'}}</b>,
       certify that I have relevant knowledge of the association and that I am authorized to make this filing.
      </p>
      <p class="certify-content">{{currentDate}}</p>
      <p class="certify-content">
        Note: It is an offence to make a false or misleading statement in
        respect of a material fact in a record submitted to the Corporate Registry for filing.
        See section 200 of the Cooperatives Association Act.
      </p>
    </div>
  </v-card>

</template>

<script lang="ts">

import { Component, Vue, Prop } from 'vue-property-decorator'

@Component({})
export default class Certify extends Vue {
  // Props passed into this component.
  @Prop({ default: '' })
  private certifiedBy: string

  @Prop({ default: '' })
  private currentDate: string

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
  @import '../../assets/styles/theme.scss';

  .certify-content{
    color: black;
    font-size: 1rem;
    line-height: 1.5rem;
  }

  certify-container{
    margin-top: 1rem;
    padding-top: 1rem;
    font-size: 0.875rem;
  }
</style>
