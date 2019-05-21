<template>
  <v-card class="support-info-card">
    <div class="container">
      <header>Need Assistance?</header>
      <p>For support or questions about this application, please contact us at:</p>
      <ul class="contact-list">
        <li class="contact-list__row">
          <v-icon small color="primary">phone</v-icon>
          <span class="contact-info__value">250 952-0568</span>
        </li>
        <li class="contact-list__row">
          <v-icon small color="primary">email</v-icon>
          <span class="contact-info__value"><a v-bind:href="'mailto:SBC_ITOperationsSupport@gov.bc.ca'">SBC_ITOperationsSupport@gov.bc.ca</a></span>
        </li>
      </ul>
    </div>
  </v-card>
</template>

<script lang="ts">
export default {
  name: 'SupportInfoCard'
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .support-info-card
    font-size 1rem
    font-weight 300

  header
    margin-bottom 1rem
    font-size 1.15em
    font-weight 500

  p
    font-size 1em

  .container
    padding-top 1.125rem

  @media (min-width 960px)
    header
      font-size 1.15em

  .contact-list
    margin-top 1.5rem
    padding 0
    font-size 0.875em
    font-weight 500
    list-style-type none

  .contact-list__row
    overflow hidden
    white-space nowrap
    text-overflow ellipsis

  .contact-list__row .v-icon
      vertical-align middle
      margin-top -0.15rem
      margin-right 1rem

  .contact-list__row + .contact-list__row
    margin-top 0.2rem
</style>