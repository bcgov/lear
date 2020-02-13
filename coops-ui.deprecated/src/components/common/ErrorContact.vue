<template>
  <ul class="pl-0">
    <li class="contact-container">
      <v-icon small class="contact-icon">mdi-phone</v-icon>
      <span class="font-weight-bold contact-key">Canada &amp; U.S. Toll Free:</span>
      <a href="tel:+1-877-526-1526" class="contact-value">1-877-526-1526</a>
    </li>
    <li class="contact-container">
      <v-icon small class="contact-icon">mdi-phone</v-icon>
      <span class="font-weight-bold contact-key">Victoria Office:</span>
      <a href="tel:+1-250-952-0568" class="contact-value">250 952-0568</a>
    </li>
    <li class="contact-container">
      <v-icon small class="contact-icon">mdi-email</v-icon>
      <span class="font-weight-bold contact-key">BC Registries Email:</span>
      <a href="mailto:BCRegistries@gov.bc.ca" class="contact-value">BCRegistries@gov.bc.ca</a>
    </li>
  </ul>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'

@Component({})
export default class ErrorContact extends Vue { }
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';

li {
  font-size: 0.9rem;
}

.contact-container {
  display: flex;

  .contact-icon {
    flex: 0 0 1.375rem;
    justify-content: flex-start;
  }

  .contact-key {
    width: 11rem;
  }

  .contact-value {
    flex: 1 1;
  }
}
</style>
