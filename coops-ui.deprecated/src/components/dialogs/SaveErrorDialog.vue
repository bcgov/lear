<template>
  <v-dialog v-model="dialog" width="45rem" persistent :attach="attach" content-class="save-error-dialog">
      <v-card>
        <v-card-title id="dialog-title" v-if="errors.length > 0 || warnings.length < 1">
          Unable to save {{filing}}
        </v-card-title>
        <v-card-title id="dialog-title" v-else>
          {{filing}} saved with warnings
        </v-card-title>

        <v-card-text id="dialog-text">
          <div class="genErr" v-if="(errors.length + warnings.length) < 1">
            <p>We were unable to save your {{filing}}. You can continue to try to save this
            filing or you can exit without saving and re-create this filing at another time.</p>
            <p>If you exit this filing, any changes you've made will not be saved.</p>
          </div>

          <div class="genErr mb-4" v-if="errors.length > 0">
            <p>We were unable to save your {{filing}} due to the following errors:</p>
            <ul>
              <li v-for="(error, index) in errors" :key="index">{{error.error}}</li>
            </ul>
          </div>

          <div class="genErr mb-4" v-if="warnings.length > 0">
            <p>Please note the following warnings:</p>
            <ul>
              <li v-for="(warning, index) in warnings" :key="index">{{warning.warning}}</li>
            </ul>
          </div>

          <template v-if="!isRoleStaff">
            <p class="genErr">If you need help, please contact us.</p>
            <ErrorContact class="mt-5" />
          </template>
        </v-card-text>

        <v-divider class="my-0"></v-divider>

        <v-card-actions v-if="(errors.length + warnings.length) < 1">
          <v-btn id="dialog-exit-button" color="primary" text @click="exit()">Exit without saving</v-btn>
          <v-spacer></v-spacer>
          <v-btn id="dialog-retry-button" color="primary" text @click="retry()" :disabled="disableRetry">Retry</v-btn>
        </v-card-actions>
        <v-card-actions v-else>
          <v-spacer></v-spacer>
          <v-btn id="dialog-ok-button" color="primary" text @click="okay()">OK</v-btn>
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
export default class SaveErrorDialog extends Vue {
  // Getter definition for static type checking.
  readonly isRoleStaff!: boolean

  // Prop containing filing name.
  @Prop({ default: 'Filing' }) private filing: string

  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to provide attachment selector.
  @Prop() private attach: string

  // Prop to disable the Retry button.
  @Prop() private disableRetry: boolean

  // Prop containing error messages.
  @Prop({ default: () => [] }) private errors: object[]

  // Prop containing warning messages.
  @Prop({ default: () => [] }) private warnings: object[]

  // Pass click events to parent.
  @Emit() private exit () { }
  @Emit() private retry () { }
  @Emit() private okay () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
