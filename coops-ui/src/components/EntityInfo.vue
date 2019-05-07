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
  name: 'EntityInfo.vue',
  computed: {
    entityName () {
      if (this.$store.state.entityName == null) return ''
      return this.$store.state.entityName
    },
    entityStatus () {
      if (this.$store.state.entityStatus == null) return ''
      return this.$store.state.entityStatus
    },
    entityBusinessNo () {
      if (this.$store.state.entityBusinessNo == null) return 'Not Available'
      return this.$store.state.entityBusinessNo
    },
    entityIncNo () {
      if (this.$store.state.entityIncNo == null) return 'Not Available'
      return this.$store.state.entityIncNo
    }
  },

  // Placeholder Data
  data () {
    return {
    }
  },
  methods: {
  },
  mounted () {
  },
  watch: {
  }
}
</script>

<style lang="stylus" scoped>
  // TODO: Explore how to expose this globally without having to include in each module
  @import "../assets/styles/theme.styl";

  #entity-info
    background #fff

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
    font-size 0.8375rem

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
