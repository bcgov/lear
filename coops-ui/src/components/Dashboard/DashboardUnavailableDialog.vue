<template>
  <v-dialog v-model="dialog" width="45rem" persistent>
    <v-card>
      <v-card-title>Dashboard Unavailable</v-card-title>
      <v-card-text>
        <p class="genErr">We are currently unable to access your dashboard. You can retry to access
          your dashboard now, or you can exit and try to access your dashboard at another time.</p>
        <p class="genErr">If this error persists, please contact us.</p>
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
      <v-divider></v-divider>
      <v-card-actions>
        <v-btn color="primary" text @click="exit()">Exit</v-btn>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="retry()">Retry</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component
export default class DashboardUnavailableDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Pass click events to parent.
  @Emit() private exit () { }
  @Emit() private retry () { }
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
