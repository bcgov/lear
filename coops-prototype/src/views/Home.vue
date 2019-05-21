<template>
  <v-container class="view-container">
    <article>
      <header>
        <h1>File BC Co-operative Annual Reports</h1>
        <p>Sign in to start filing your BC Co-operative Annual Report. You will need to provide your <strong>Incorporation Number</strong> and your <strong>Passcode</strong> in the letter you received in the mail.</p>
      </header>
      <section>
        <v-card flat>
          <v-container class="passcode-container">
            <Passcode/>
          </v-container>
        </v-card>
      </section>
    </article>
    <aside>
      <SupportInfoCard/>
    </aside>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import EntityInfo from '@/components/EntityInfo.vue'
import Passcode from '@/components/Passcode.vue'
import SupportInfoCard from '@/components/SupportInfoCard.vue'

@Component({
  components: {
    EntityInfo,
    Passcode,
    SupportInfoCard
  }
})
export default class Home extends Vue {}
</script>

<style scoped lang="stylus">
  @import "../assets/styles/theme.styl"

  header h1
    margin-bottom 2rem

  header p
    font-size 1.125rem
    font-weight 300

  strong
    font-weight 600

  .passcode-container
    padding 2rem

</style>