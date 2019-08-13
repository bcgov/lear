<template>
  <div class="entity-info">
    <v-container>
      <div class="title-container">
        <div class="entity-name">{{ entityName || 'Not Available' }}</div>
        <!-- TODO: Discuss/decide how we are handling entity statuses (e.g. 'GOODSTANDING' etc.) -->
        <v-chip class="entity-status" label small disabled text-color="white" v-if="entityStatus"
          :class="{
            'blue' : entityStatus === 'GOODSTANDING',
            'red' : entityStatus === 'PENDINGDISSOLUTION' | 'NOTINCOMPLIANCE',
          }">
          <!-- TODO: These strings should be pulled out into a globally accessible file -->
          <span v-if="entityStatus === 'GOODSTANDING'">In Good Standing</span>
          <span v-else-if="entityStatus === 'PENDINGDISSOLUTION'">Pending Dissolution</span>
          <span v-else-if="entityStatus === 'NOTINCOMPLIANCE'">Not in Compliance</span>
        </v-chip>
      </div>
      <dl class="meta-container">
        <dt>Business No:</dt>
        <!-- TODO: These strings should be pulled out into a globally accessible file (e.g. 'Not Available') -->
        <dd class="business-number">{{ entityBusinessNo || 'Not Available' }}</dd>
        <dt>Incorporation No:</dt>
        <dd class="incorp-number">{{ entityIncNo || 'Not Available' }}</dd>
      </dl>
    </v-container>
  </div>
</template>

<script>
import axios from '@/axios-auth'
import DateUtils from '@/DateUtils'
import { mapState, mapActions } from 'vuex'

export default {
  name: 'EntityInfo',

  mixins: [DateUtils],

  computed: {
    ...mapState(['entityName', 'entityStatus', 'entityBusinessNo', 'entityIncNo', 'corpNum'])
  },

  mounted () {
    this.getEntityInfo()
  },

  methods: {
    ...mapActions(['setEntityName', 'setEntityStatus', 'setEntityBusinessNo', 'setEntityIncNo',
      'setLastAgmDate', 'setEntityFoundingDate', 'setLastPreLoadFilingDate']),

    getEntityInfo () {
      if (this.corpNum) {
        const url = this.corpNum
        axios.get(url)
          .then(response => {
            if (response && response.data && response.data.business) {
              this.setEntityName(response.data.business.legalName)
              this.setEntityStatus(response.data.business.status)
              this.setEntityBusinessNo(response.data.business.taxId)
              this.setEntityIncNo(response.data.business.identifier)
              this.setLastPreLoadFilingDate(response.data.business.lastLedgerTimestamp
                ? response.data.business.lastLedgerTimestamp.split('T')[0] : null)
              this.setEntityFoundingDate(response.data.business.foundingDate
                ? response.data.business.foundingDate.split('T')[0] : null)
              const date = response.data.business.lastAnnualGeneralMeetingDate
              if (
                date &&
                date.length === 10 &&
                date.indexOf('-') === 4 &&
                date.indexOf('-', 5) === 7 &&
                date.indexOf('-', 8) === -1
              ) {
                this.setLastAgmDate(date)
              } else {
                this.setLastAgmDate(null)
              }
            } else {
              console.log('getEntityInfo() error - invalid response data')
            }
          })
          .catch(error => console.error('getEntityInfo() error =', error))
      }
    }
  }
}
</script>

<style lang="stylus" scoped>
  // TODO: Explore how to expose this globally without having to include in each module
  @import "../assets/styles/theme.styl";

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
