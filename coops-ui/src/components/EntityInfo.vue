<template>
  <div class="entity-info" :class="{ 'staff': isRoleStaff }">
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

      <div class="business-info">
        <div class="info-left">
          <dl class="meta-container">
            <dt>Business No:</dt>
            <dd class="business-number ml-2">{{ entityBusinessNo || 'Not Available' }}</dd>
            <dt class="bulletBefore">Incorporation No:</dt>
            <dd class="incorp-number ml-2">{{ entityIncNo || 'Not Available' }}</dd>
          </dl>
        </div>

        <div class="info-right">
          <dl class="meta-container">
            <dt class="sr-only">Business Email:</dt>
            <dd class="business-email" aria-label="Business Email">{{businessEmail || 'Unknown Email'}}</dd>
            <template v-if="fullPhoneNumber">
              <dt class="sr-only">Business Phone:</dt>
              <dd class="business-phone bulletBefore" aria-label="Business Phone">{{fullPhoneNumber}}</dd>
            </template>
          </dl>
          <v-menu bottom left offset-y content-class="v-menu">
            <template v-slot:activator="{ on }">
              <v-btn small flat v-on="on" color="primary">
                <v-icon small>settings</v-icon>
              </v-btn>
            </template>
            <v-list>
              <v-list-tile @click="editBusinessProfile">
                <v-list-tile-title>Update business profile</v-list-tile-title>
              </v-list-tile>
            </v-list>
          </v-menu>
        </div>
      </div>

    </v-container>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { mapState, mapGetters } from 'vuex'

@Component({
  computed: {
    // Property definitions for runtime environment.
    ...mapState(['entityName', 'entityStatus', 'entityBusinessNo', 'entityIncNo',
      'businessEmail', 'businessPhone', 'businessPhoneExtension']),
    ...mapGetters(['isRoleStaff'])
  }
})
export default class EntityInfo extends Vue {
  // Local definitions of computed properties for static type checking.
  // Use non-null assertion operator to allow use before assignment.
  readonly entityName!: string
  readonly entityStatus!: string
  readonly entityBusinessNo!: string
  readonly entityIncNo!: number
  readonly businessEmail!: string
  readonly businessPhone!: string
  readonly businessPhoneExtension!: string
  readonly isRoleStaff!: boolean

  /**
   * Computed value.
   * @returns The business phone number and optional extension, or null.
   */
  private get fullPhoneNumber (): string {
    if (!this.businessPhone) return null
    return `${this.businessPhone}${this.businessPhoneExtension ? (' x' + this.businessPhoneExtension) : ''}`
  }

  /**
   * Redirects the user to the Auth UI to update their business profile.
   */
  private editBusinessProfile (): void {
    let authStub = sessionStorage.getItem('AUTH_URL') || ''
    if (!(authStub.endsWith('/'))) { authStub += '/' }
    const authURL = authStub + 'businessprofile'
    // assume Auth URL is always reachable
    window.location.assign(authURL)
  }
}
</script>

<!-- eslint-disable max-len -->
<style lang="stylus" scoped>
  // TODO: Explore how to expose this globally without having to include in each module
  @import "../assets/styles/theme.styl"

  .entity-info
    background #ffffff

  .entity-info.staff
    // background-image url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='105' height='100'><text x='0' y='105' font-size='30' transform='rotate(-45 10,40)' opacity='0.1'>STAFF</text></svg>")
    // background-repeat repeat-x

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
    margin-top: 0.25rem
    margin-left 0.5rem
    vertical-align top

  .business-info
    display flex
    direction row

    .info-right
      margin-top 0
      margin-right 0
      margin-left auto

  .meta-container
    display inline-block
    overflow hidden
    color $gray6
    font-size 0.875rem

  dd, dt
    float left

  dt
    position relative

  .bulletBefore
    &:before
      content '•'
      display inline-block
      margin-right 0.75rem
      margin-left 0.75rem

  .v-btn
    margin 0 0 0 0.5rem
    bottom 0.5rem

  .v-menu
    .v-list
      padding 0

      .v-list__tile__title
        font-size 0.875rem
</style>
