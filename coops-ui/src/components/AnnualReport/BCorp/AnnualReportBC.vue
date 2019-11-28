<template>
  <article id="annual-report-article">
    <header>
      <h1 id="AR-header-BC">File {{ ARFilingYear }} Annual Report</h1>
      <p>Please review all the information before you file and pay.</p>
    </header>

    <div>
      <!-- Annual Report Date -->
      <section>
        <header>
          <h2 id="AR-header-1-BC">Business Details</h2>
        </header>
        <ARDate />
        <br>
        <SummaryOfficeAddresses
          :registeredAddress="registeredAddress"
          :recordsAddress="recordsAddress"
        />
      </section>

      <!-- Director Information -->
      <section>
        <header>
          <h2 id="AR-header-2-BC">Directors</h2>
        </header>
        <SummaryDirectors
          :directors="directors"
        />
      </section>
    </div>

    <!-- Certify -->
    <section>
      <header>
        <h2 id="AR-step-4-header">Certify Correct</h2>
        <p>Enter the name of the current director, officer, or lawyer submitting this Annual Report.</p>
      </header>
      <Certify
        :isCertified.sync="isCertified"
        :certifiedBy.sync="certifiedBy"
        :currentDate="currentDate"
        @valid="certifyFormValid=$event"
      />
    </section>

    <!-- Staff Payment -->
    <section v-if="isRoleStaff && isPayRequired">
      <header>
        <h2 id="AR-step-5-header">5. Staff Payment</h2>
      </header>
      <StaffPayment
        :value.sync="routingSlipNumber"
        @valid="staffPaymentFormValid=$event"
      />
    </section>
  </article>

</template>

<script lang="ts">
// // Libraries
import { Component, Prop, Vue } from 'vue-property-decorator'

import ARDate from '@/components/AnnualReport/BCorp/ARDate.vue'
import Certify from '@/components/AnnualReport/Certify.vue'
import StaffPayment from '@/components/AnnualReport/StaffPayment.vue'
import { SummaryOfficeAddresses, SummaryDirectors } from '@/components/Common'

@Component({
  components: {
    ARDate,
    SummaryOfficeAddresses,
    SummaryDirectors,
    Certify,
    StaffPayment
  }
})
export default class AnnualReportBC extends Vue {

}
</script>

<style lang="scss" scoped>
  @import '../../assets/styles/theme.scss';

</style>
