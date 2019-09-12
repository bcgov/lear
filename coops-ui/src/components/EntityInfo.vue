<template>
  <div class="entity-info" :class=role>
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

    <!-- BUSINESS CONTACT INFO -->
    <div >
      <span>{{businessEmail || 'No Email'}}</span>
      &nbsp;&middot;&nbsp;
      <span>{{businessPhone || 'No Phone'}}</span>
      <v-menu offset-y>
        <template v-slot:activator="{ on }">
          <v-btn small flat v-on="on">
            <v-icon>keyboard_arrow_down</v-icon>
          </v-btn>
        </template>
        <v-list>
          <v-list-tile @click="editBusinessProfile">
            <v-list-tile-title>Edit contact information</v-list-tile-title>
          </v-list-tile>
        </v-list>
      </v-menu>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex'

export default {
  name: 'EntityInfo',

  computed: {
    ...mapState(['role', 'entityName', 'entityStatus', 'entityBusinessNo', 'entityIncNo',
      'businessEmail', 'businessPhone'])
  },

  methods: {
    editBusinessProfile () {
      let authStub = sessionStorage.getItem('AUTH_URL') || ''
      if (!(authStub.endsWith('/'))) { authStub += '/' }
      const authURL = authStub + 'businessprofile'
      // assume Auth URL is always reachable
      window.location.assign(authURL)
    }
  }
}
</script>

<!-- eslint-disable max-len -->
<style lang="stylus" scoped>
  // TODO: Explore how to expose this globally without having to include in each module
  @import "../assets/styles/theme.styl"

  .entity-info
    background #ffffff
    background-repeat repeat-x

  .entity-info.owner
    // background-image url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='130' height='100'><text x='0' y='108' font-size='30' transform='rotate(-45 10,40)' opacity='0.1'>OWNER</text></svg>")

  .entity-info.staff
    // background-image url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='100'><text x='0' y='95' font-size='30' transform='rotate(-45 10,40)' opacity='0.1'>STAFF</text></svg>")

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
