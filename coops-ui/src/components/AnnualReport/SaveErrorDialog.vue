<template>
  <v-dialog v-model="dialog" width="50rem">
    <v-card>
      <v-card-title>Unable to Save Filing</v-card-title>
      <v-card-text>
        <p class="genErr">We were unable to save your filing. You can continue to try to save this
            filing or you can exit without saving and re-create this filing at another time.</p>
        <p  class="genErr">If you exit this filing, any changes you've made will not be saved.</p>
        <p class="genErr">
          <v-icon small>phone</v-icon>
          <a href="tel:+1-250-952-0568" class="error-dialog-padding">250 952-0568</a>
        </p>
        <p class="genErr">
          <v-icon small>email</v-icon>
          <a href="mailto:SBC_ITOperationsSupport@gov.bc.ca" class="error-dialog-padding"
            >SBC_ITOperationsSupport@gov.bc.ca</a>
        </p>
      </v-card-text>
      <v-divider class="my-0"></v-divider>
      <v-card-actions>
        <v-btn color="primary" flat @click="exit()">Exit without saving</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" flat @click="retry()" :disabled="disableRetry">Retry</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component
export default class SaveErrorDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to disable the Retry button.
  @Prop() private disableRetry: boolean

  // Pass click events to parent.
  @Emit() private exit () { }
  @Emit() private retry () { }
}
</script>

<style lang="stylus" scoped>
@import '../../assets/styles/theme.styl'

.genErr
  font-size: 0.9rem;

.error-dialog-padding
  margin-left: 1rem;
</style>
