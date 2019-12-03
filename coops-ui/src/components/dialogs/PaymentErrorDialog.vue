<template>
  <v-dialog v-model="dialog" width="45rem" persistent :attach="attach" content-class="payment-error-dialog">
    <v-card>
      <v-card-title>Unable to Process Payment</v-card-title>

      <v-card-text>
        <p class="genErr">We are unable to process payments at this time.</p>
        <p class="genErr">Your filing has been saved as a DRAFT and you can resume
          your filing from the Business Dashboard at a later time.</p>

        <template v-if="!isRoleStaff">
          <p class="genErr">PayBC is normally available:</p>
          <p class="genErr">
            Monday to Friday: 6:00am to 9:00pm
            <br>Saturday: 12:00am to 7:00pm
            <br>Sunday: 12:00pm to 12:00am
          </p>

          <p class="genErr">If this error persists, please contact us.</p>
          <ErrorContact />
        </template>
      </v-card-text>

      <v-divider class="my-0"></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn id="dialog-exit-button" color="primary" text @click="exit()">Back to My Dashboard</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import { mapGetters } from 'vuex'
import { ErrorContact } from '@/components/common'

@Component({
  computed: {
    // Property definition for runtime environment.
    ...mapGetters(['isRoleStaff'])
  },
  components: { ErrorContact }
})
export default class PaymentErrorDialog extends Vue {
  // Getter definition for static type checking.
  readonly isRoleStaff!: boolean

  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to provide attachment selector.
  @Prop() private attach: string

  // Pass click event to parent.
  @Emit() private exit () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
