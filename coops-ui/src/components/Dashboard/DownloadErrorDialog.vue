<template>
  <v-dialog v-model="dialog" width="45rem">
    <v-card>
      <v-card-title>Unable to Download Document</v-card-title>
      <v-card-text>
        <p class="genErr">We were unable to download your filing history document(s).</p>
        <p class="genErr">If this error persists, please contact us.</p>
        <p class="genErr">
          <v-icon small>mdi-phone</v-icon>
          <a href="tel:+1-250-952-0568" class="error-dialog-padding">250 952-0568</a>
        </p>
        <p class="genErr">
          <v-icon small>mdi-email</v-icon>
          <a href="mailto:SBC_ITOperationsSupport@gov.bc.ca" class="error-dialog-padding"
            >SBC_ITOperationsSupport@gov.bc.ca</a>
        </p>
      </v-card-text>
      <v-divider class="my-0"></v-divider>
      <v-card-actions>
        <v-btn color="primary" text @click="close()">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component
export default class DownloadErrorDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Pass click events to parent.
  @Emit() private close () { }
}
</script>

<style lang="scss" scoped>
@import '../../assets/styles/theme.scss';

.genErr{
  font-size: 0.9rem;
}

.error-dialog-padding{
  margin-left: 1rem;
}
</style>
