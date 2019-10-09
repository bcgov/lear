<template>
  <div class="entity-info" :class="{ 'staff': isRoleStaff }">
    <v-container>

      <!-- Business Name, Business Status -->
      <div class="title-container">
<<<<<<< HEAD
        <div class="entity-name mb-1">{{ entityName || 'Not Available' }}</div>
=======
        <div class="entity-name">{{ entityName || 'Not Available' }}</div>
>>>>>>> Add mailing address to director (#367)
        <v-chip class="entity-status" small label text-color="white" v-if="entityStatus"
          :class="{
            'blue' : entityStatus === 'GOODSTANDING',
            'red' : entityStatus === 'PENDINGDISSOLUTION' | 'NOTINCOMPLIANCE',
          }">
          <span v-if="entityStatus === 'GOODSTANDING'">In Good Standing</span>
          <span v-else-if="entityStatus === 'PENDINGDISSOLUTION'">Pending Dissolution</span>
          <span v-else-if="entityStatus === 'NOTINCOMPLIANCE'">Not in Compliance</span>
        </v-chip>
      </div>

      <!-- Business Numbers, Contact Info -->
      <div class="business-info">
        <dl>
          <dt>Business No:</dt>
          <dd class="ml-2 business-number">{{ entityBusinessNo || 'Not Available' }}</dd>
          <dt>Incorporation No:</dt>
          <dd class="ml-2 incorp-number">{{ entityIncNo || 'Not Available' }}</dd>
        </dl>

        <div class="business-info__contact">
          <dl>
            <dt class="sr-only">Business Email:</dt>
            <dd class="business-email" aria-label="Business Email">{{businessEmail || 'Unknown Email'}}</dd>
            <template v-if="fullPhoneNumber">
              <dt class="sr-only">Business Phone:</dt>
              <dd class="business-phone bulletBefore" aria-label="Business Phone">{{fullPhoneNumber}}</dd>
            </template>
          </dl>
          <v-menu bottom left offset-y content-class="v-menu">
            <template v-slot:activator="{ on }">
<<<<<<< HEAD
              <v-btn small icon color="primary" class="business-info__settings-btn" v-on="on">
                <v-icon small>mdi-settings</v-icon>
              </v-btn>
            </template>
            <v-list class="pt-0 pb-0">
=======
              <v-btn small text v-on="on" color="primary">
                <v-icon small>mdi-settings</v-icon>
              </v-btn>
            </template>
            <v-list>
>>>>>>> Add mailing address to director (#367)
              <v-list-item @click="editBusinessProfile">
                <v-list-item-title>Update business profile</v-list-item-title>
              </v-list-item>
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
    const authUrl = sessionStorage.getItem('AUTH_URL')
    const businessProfileUrl = authUrl + 'businessprofile'

    // assume Business Profile URL is always reachable
    window.location.assign(businessProfileUrl)
  }
}
</script>

<!-- eslint-disable max-len -->
<style lang="scss" scoped>
// TODO: Explore how to expose this globally without having to include in each module
@import "../assets/styles/theme.scss";

.entity-info {
  background: #ffffff;
}

<<<<<<< HEAD
=======
// .entity-info.staff {
//   background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='105' height='100'><text x='0' y='105' font-size='30' transform='rotate(-45 10,40)' opacity='0.1'>STAFF</text></svg>");
//   background-repeat: repeat-x;
// }

>>>>>>> Add mailing address to director (#367)
.container {
  padding-top: 1.5rem;
  padding-bottom: 1.5rem;
}

<<<<<<< HEAD
.entity-name {
  display: inline-block;
  color: $gray9;
  letter-spacing: -0.01rem;
  font-size: 1.125rem;
  font-weight: 700;
=======
.title-container {
  margin-top: -0.2rem;
}

.entity-name {
  margin-top: 0.125rem;
  margin-bottom: 0.25rem;
  display: inline-block;
  font-size: 1.125rem;
  font-weight: 600;
>>>>>>> Add mailing address to director (#367)
}

.entity-status {
  margin-top: 0.25rem;
  margin-left: 0.5rem;
  vertical-align: top;
}

.business-info {
  display: flex;
  direction: row;
<<<<<<< HEAD
  justify-content: space-between;
}

dl {
  display: inline-block;
  overflow: hidden;
  color: $gray6;
=======

  .info-right {
    margin-top: 0;
    margin-right: 0;
    margin-left: auto;
  }
}

.meta-container {
  display: inline-block;
  overflow: hidden;
  color: $gray6;
  font-size: 0.875rem;
>>>>>>> Add mailing address to director (#367)
}

dd, dt {
  float: left;
}

dt {
  position: relative;
}

<<<<<<< HEAD
dd + dt:before {
  content: "•";
    display: inline-block;
    margin-right: 0.75rem;
    margin-left: 0.75rem;
}

.business-info__contact {
  display: flex;
  align-items: center;
}

.business-info__settings-btn {
  margin-top: 0.1rem;
  margin-left: 0.25rem;
=======
.bulletBefore {
   &:before {
    content: "•";
    display: inline-block;
    margin-right: 0.75rem;
    margin-left: 0.75rem;
  }
}

.v-btn {
  margin: 0 0 0 0.5rem;
  bottom: 0.5rem;
}

.v-menu {
  .v-list {
    padding: 0;
    .v-list__tile__title {
      font-size: 0.875rem;
    }
  }
>>>>>>> Add mailing address to director (#367)
}
</style>
