<template>
  <v-dialog v-model="dialog" width="45rem" persistent>
    <v-card>
      <v-card-title>Account Authorization</v-card-title>
      <v-card-text>
        <p class="genErr">This account appears to be unable to access this business. You can
          retry to access this business now, or you can exit and return to the login page.</p>
        <p class="genErr">If this error persists, please contact us.</p>
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
      <v-divider></v-divider>
      <v-card-actions>
        <v-btn color="primary" flat @click="exit()">Exit</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" flat @click="retry()">Retry</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component
export default class AccountAuthorizationDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

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
