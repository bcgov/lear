<template>
  <v-dialog v-model="dialog" width="45rem">
    <v-card>
      <v-card-title>Unable to Process Payment</v-card-title>
      <v-card-text>
        <p class="genErr">PayBC is unable to process payments at this time.</p>
        <p class="genErr">Your filing has been saved as a DRAFT and you can resume your filing from your Dashboard
          at a later time.</p>
        <p class="genErr">PayBC is normally available:</p>
        <p class="genErr">
          Monday to Friday: 6:00am to 9:00pm
          <br>Saturday: 12:00am to 7:00pm
          <br>Sunday: 12:00pm to 12:00am
        </p>

        <ErrorContact />

      </v-card-text>
      <v-divider class="my-0"></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="exit()">Back to My Dashboard</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import ErrorContact from '@/components/ErrorContact.vue'

@Component({
  components: { ErrorContact }
})
export default class PaymentErrorDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Pass click event to parent.
  @Emit() private exit () { }
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/theme.scss';

.genErr{
  font-size: 0.9rem;
}
</style>
