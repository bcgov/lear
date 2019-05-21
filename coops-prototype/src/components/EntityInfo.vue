<template>
  <div id="entity-info">
    <v-container>
        <div class="title-container">
          <div class="entity-name">{{ entityName }}</div>
        </div>

        <dl class="meta-container">
          <dt>Business No:</dt>
          <!-- TODO: Strings should be pulled out into a globally accessible file (e.g. 'Not Available') -->
          <dd class="business-number">{{ entityBusinessNo ? entityBusinessNo : 'Not Available' }}</dd>
          <dt>Incorporation No:</dt>
          <dd class="incorp-number">{{ entityIncNo ? entityIncNo : 'Not Available' }}</dd>
        </dl>
    </v-container>
  </div>
</template>

<script>
export default {
  name: 'entity-info',

  // Placeholder Data
  data () {
    return {
      entityName: 'My Business Name',
      entityStatus: 'GOODSTANDING',
      entityBusinessNo: '123456789',
      entityIncNo: '123456789'
    }
  }
}
</script>

<style lang="stylus" scoped>
  // TODO: Explore how to expose this globally without having to include in each module
  @import "../assets/styles/theme.styl";

  #entity-info
    background #ffffff

  .title-container
    margin-top -0.2rem

  .entity-name
    display inline-block
    font-size 1.25rem
    font-weight 600

  .entity-status
    margin-left 0.5rem

  .meta-container
    overflow hidden
    color $gray6
    font-size 0.8375rem
    font-weight 500

  dd, dt
    float left

  dt
    position: relative;

  dd
    margin-left 0.5rem;

    + dt
      &:before
        content '•'
        display inline-block
        margin-right 0.75rem
        margin-left 0.75rem

  .v-chip
    margin-top: 0.25rem
    vertical-align top
</style>
