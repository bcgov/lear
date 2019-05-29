<template>
  <div>
    <EntityInfo/>
      <v-container class="view-container">
        <article>
          <v-stepper alt-labels flat>
            <v-stepper-header>
              <v-stepper-step step="1">Annual General Meeting</v-stepper-step>
              <v-divider></v-divider>
              <v-stepper-step step="2">Office Addresses</v-stepper-step>
              <v-divider></v-divider>
              <v-stepper-step step="3">Directors</v-stepper-step>
              <v-divider></v-divider>
              <v-stepper-step step="4">Certify & File</v-stepper-step>
            </v-stepper-header>
          </v-stepper>

          <header>
            <h1>Annual General Meeting Date</h1>
            <p class="step-description">When did you hold your 2018 Annual General Meeting?</p>
            <!--
            <v-menu
              v-model="menu1"
              :close-on-content-click="false"
              full-width
              max-width="290">
              <template v-slot:activator="{ on }">
                <v-text-field
                  :value="computedDateFormattedMomentjs"
                  clearable
                  label="Annual General Meeting Date"
                  box
                  readonly
                  v-on="on"
                ></v-text-field>
              </template>
              <v-date-picker
                no-title
                v-model="date"
                @change="menu1 = false"
              ></v-date-picker>
            </v-menu>
            -->
            <!--
            <v-checkbox class="noAgm-checkbox" color="primary" label="No Annual General Meeting was held this year" v-model="noAgmDate"></v-checkbox>
            -->
          </header>
        </article>
      </v-container>
      <v-container>
        <div class="step-btns">
          <v-btn class="next-btn" large color="primary" to="/AnnualReportStep2">
            <span>Next: Update Directors</span>
            <v-icon>arrow_right</v-icon>
          </v-btn>
        </div>
      </v-container>
  </div>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator'
  import EntityInfo from '@/components/EntityInfo.vue'
  import moment from 'moment'

  export default {
    name: "AnnualReportStep1",

    components: {
      EntityInfo
    },

    data () {
      return {
        noAgmDate: false,
        date: new Date().toISOString().substr(0, 10)
      }
    },

    computed: {
      computedDateFormattedMomentjs () {
        return this.date ? moment(this.date).format('dddd, MMMM Do YYYY') : ''
      }
    }
  }
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  .step-description
    font-size 1.125rem

  .step-btns
    display flex
    padding-top 2rem
    border-top 1px solid $gray5

    .v-btn
      margin 0

    .v-btn + .v-btn
      margin-left 0.5rem

  .v-btn.next-btn
    margin-left auto
</style>