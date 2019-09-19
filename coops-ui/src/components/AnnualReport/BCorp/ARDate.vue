<template>
  <v-card flat class="container">
    <div class="timeline">
        <span class="title">Annual Report Date</span>
        <span class="date">Sept 01, 2019</span>
        <span class="title">Filing Date</span>
        <span class="date">Today (Sept 16, 2019)</span>
      </div>
  </v-card>
</template>w
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'

@Component
export default class ARDate extends Vue {
  // TODO: Retrieve Dates Data Dynamically.
}
</script>
<style lang="stylus" scoped>
  @import '../../../assets/styles/theme.styl'

  .container
    background: #FFFFFF

    .timeline
      display: flex

      .title
        color: #262626
        font-size: 1rem
        font-weight: 500
        line-height: 1.2rem

      .date
        color: #262626
        font-family: "BC Sans"
        font-size: 0.875rem
        line-height: 1.125rem
        margin: 0 3.125rem 0

</style>
