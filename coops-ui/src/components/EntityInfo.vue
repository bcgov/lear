<template>
  <div class="entity-info">
    <v-container>
      <div class="title-container">
        <div class="entity-name">{{ entityName || 'Not Available' }}</div>
        <v-chip class="entity-status" label small disabled text-color="white" v-if="entityStatus"
          :class="{
            'blue' : entityStatus === 'GOODSTANDING',
            'red' : entityStatus === 'PENDINGDISSOLUTION' | 'NOTINCOMPLIANCE',
          }">
          <span v-if="entityStatus === 'GOODSTANDING'">In Good Standing</span>
          <span v-else-if="entityStatus === 'PENDINGDISSOLUTION'">Pending Dissolution</span>
          <span v-else-if="entityStatus === 'NOTINCOMPLIANCE'">Not in Compliance</span>
        </v-chip>
      </div>
      <dl class="meta-container">
        <dt>Business No:</dt>
        <dd class="business-number">{{ entityBusinessNo || 'Not Available' }}</dd>
        <dt>Incorporation No:</dt>
        <dd class="incorp-number">{{ entityIncNo || 'Not Available' }}</dd>
      </dl>
    </v-container>
  </div>
</template>

<script>
import { mapState } from 'vuex'

export default {
  name: 'EntityInfo',

  computed: {
    ...mapState(['entityName', 'entityStatus', 'entityBusinessNo', 'entityIncNo'])
  }
}
</script>

<style lang="stylus" scoped>
  // TODO: Explore how to expose this globally without having to include in each module
  @import "../assets/styles/theme.styl"

  .entity-info
    background #ffffff

  .container
    padding-top 1.5rem
    padding-bottom 1.5rem

  .title-container
    margin-top -0.2rem

  .entity-name
    margin-top 0.125rem
    margin-bottom 0.25rem
    display inline-block
    font-size 1.125rem
    font-weight 600

  .entity-status
    margin-left 0.5rem

  .meta-container
    overflow hidden
    color $gray6
    font-size 0.875rem

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
