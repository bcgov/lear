<template>
  <v-dialog v-model="dialog" width="60rem">
      <v-card>
        <v-card-title id="error-dialogue-title" v-if="errors.length > 0 || warnings.length < 1">
          Unable to save {{filing}}
        </v-card-title>
        <v-card-title id="warning-dialogue-title" v-else>
          {{filing}} saved with warnings
        </v-card-title>

        <v-card-text id="dialogue-text">
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

          <p class="genErr">If you need help, please contact us.</p>

          <ErrorContact class="mt-5" />

        </v-card-text>

        <v-divider class="my-0"></v-divider>

        <v-card-actions v-if="(errors.length + warnings.length) < 1">
          <v-btn id="exit-btn" color="primary" text @click="exit()">Exit without saving</v-btn>
          <v-spacer></v-spacer>
          <v-btn id="retry-btn" color="primary" text @click="retry()" :disabled="disableRetry">Retry</v-btn>
        </v-card-actions>
        <v-card-actions v-else>
          <v-spacer></v-spacer>
          <v-btn id="okay-btn" color="primary" text @click="okay()">Okay</v-btn>
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
export default class SaveErrorDialog extends Vue {
  // Prop containing filing name.
  @Prop({ default: 'Filing' }) private filing: string

  // Prop to display the dialog.
  @Prop() private dialog: boolean

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
@import '@/assets/styles/theme.scss';

.genErr {
  font-size: 0.9rem;
}
</style>
