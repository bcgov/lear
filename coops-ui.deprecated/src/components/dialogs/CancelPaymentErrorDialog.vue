<template>
  <v-dialog v-model="dialog" width="45rem" persistent :attach="attach" content-class="cancel-payment-error-dialog">
      <v-card>
        <v-card-title id="dialog-title" data-test-id="cancel-pay-dialog-title">
          Unable to Cancel Payment
        </v-card-title>

        <v-card-text id="dialog-text" data-test-id="cancel-pay-dialog-text">
          <p class="genErr" v-if="errors.length < 1">
            We were unable to cancel your payment.
          </p>
          <p class="genErr" v-else>
            We were unable to cancel your payment due to the following errors:
          </p>
          <p class="genErr" v-for="(error, index) in errors" :key="index">
            {{error.error}}
          </p>
          <template v-if="!isRoleStaff">
            <p class="genErr">If you need help, please contact us.</p>
            <ErrorContact class="mt-5" />
          </template>
        </v-card-text>

        <v-divider class="my-0"></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn id="dialog-ok-btn" color="primary" text @click="okay()"
          data-test-id="cancel-pay-dialog-ok-btn">OK</v-btn>
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
export default class CancelPaymentErrorDialog extends Vue {
  readonly isRoleStaff!: boolean

  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to provide attachment selector.
  @Prop() private attach: string

  // Prop containing error messages.
  @Prop({ default: () => {
    return [ ]
  }
  })
    private errors: object[]

  // Pass click event to parent.
  @Emit() private okay () { }
}
</script>
