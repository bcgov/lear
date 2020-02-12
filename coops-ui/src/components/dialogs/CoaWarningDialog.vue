<template>
  <v-dialog v-model="dialog" width="45rem" persistent :attach="attach" content-class="coa-warning-dialog">
    <v-card>
      <v-card-title>Address Change Effective 12:01 AM</v-card-title>

      <v-card-text>
        <p class="genErr">Address changes take effect at 12:01 AM (Pacific Time).
          No other filings can be performed until an Address Change has taken effect.</p>
        <p class="genErr">If you need to perform other filings today, file them prior to
          your Address Change filing.</p>
      </v-card-text>

      <v-divider class="my-0"></v-divider>

      <v-card-actions>
        <v-btn id="dialog-toggle-button" color="primary" text @click="toggle()">Return to dashboard</v-btn>
        <v-spacer></v-spacer>
        <v-btn id="dialog-proceed-button" color="primary" text @click="proceed()">Continue to Change of Address</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component({})
export default class CoaWarningDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to provide attachment selector.
  @Prop() private attach: string

  // Pass click event to parent.
  @Emit() private toggle () { }

  // Pass click event to parent.
  @Emit() private proceed () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
