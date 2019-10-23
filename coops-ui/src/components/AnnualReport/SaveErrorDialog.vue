<template>
  <v-dialog v-model="dialog" width="60rem">
      <v-card>
        <v-card-title id="error-dialogue-title" v-if="errors.length > 0 || warnings.length < 1">
          Unable to Save Filing
        </v-card-title>
        <v-card-title id="warning-dialogue-title" v-else>
          Filing Saved with Warnings
        </v-card-title>
        <v-card-text id="dialogue-text">
          <p class="genErr" v-if="errors.length + warnings.length < 1">
            We were unable to save your filing. You can continue to try to save this
            filing or you can exit without saving and re-create this filing at another time.
          </p>
          <p class="genErr" v-else-if="errors.length > 0">
            We were unable to save your filing due to the following errors:
          </p>
          <p class="genErr" v-else>
            Please note the following:
          </p>
          <p class="genErr" v-if="errors.length + warnings.length < 1">
            If you exit this filing, any changes you've made will not be saved.
          </p>
          <p class="genErr" v-for="(error, index) in errors" :key="index">
            {{error.error}}
          </p>
          <p class="genErr" v-for="(warning, index) in warnings" :key="index">
            {{warning.warning}}
          </p>
          <ul class="pl-0">
            <li class="genErr contact-container">
              <v-icon small class="contact-icon">mdi-phone</v-icon>
              <span class="font-weight-bold contact-item">Canada &amp; U.S. Toll Free:</span>
              <a href="tel:+1-877-526-1526" class="contact-detail">1-877-526-1526</a>
            </li>
            <li class="genErr contact-container">
              <v-icon small class="contact-icon">mdi-phone</v-icon>
              <span class="font-weight-bold contact-item">Victoria Office:</span>
              <a href="tel:+1-250-952-0568" class="contact-detail">250 952-0568</a>
            </li>
            <li class="genErr contact-container">
              <v-icon small class="contact-icon">mdi-email</v-icon>
              <span class="font-weight-bold contact-item">BC Registries Email:</span>
              <a href="mailto:bcregistries@gov.bc.ca" class="contact-detail">bcregistries@gov.bc.ca</a>
            </li>
          </ul>
        </v-card-text>
        <v-divider class="my-0"></v-divider>
        <v-card-actions v-if="errors.length + warnings.length < 1">
          <v-btn color="primary" text @click="exit()">Exit without saving</v-btn>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="retry()" :disabled="disableRetry">Retry</v-btn>
        </v-card-actions>
        <v-card-actions v-else>
          <v-btn id="okay-btn" color="primary" text @click="okay()">Okay</v-btn>
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

  // Prop containing error messages.
  @Prop() private errors: object[]

  // Prop containing warning messages.
  @Prop() private warnings: object[]

  // Pass click events to parent.
  @Emit() private exit () { }
  @Emit() private retry () { }
  @Emit() private okay () { }
}
</script>

<style lang="scss" scoped>
@import '../../assets/styles/theme.scss';

.genErr{
  font-size: 0.9rem;
}

.contact-container {
  display: flex;

  .contact-icon {
    flex: 0 0 2rem;
    justify-content: flex-start;
  }

  .contact-item {
    width: 12rem;
  }

  .contact-detail {
    flex: 1 1;
  }
}
</style>
