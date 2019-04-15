<template>
  <div>
    <EntityInfo/>
    <v-container class="view-container">
      <article v-bind:class="{ editing: isEditing }" id="example-content">
        <header>
          <h1>File Annual Report</h1>
          <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.</p>
        </header>
        <section>
          <header>
            <h2>2. Registered Office Addresses (Expand)</h2>
            <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium</p>
          </header>
          <v-card v-bind:class="{ focused: focusAddress1 }">
            <ul>
              <li class="container">
                <v-expand-transition>
                  <div class="meta-container" v-show="!focusAddress1">
                    <label>Delivery Address</label>
                    <div class="value">
                      <div class="address-block__row">{{MailStreet1}}</div>
                      <div class="address-block__row">
                        <span>{{MailCity}}</span>
                        <span>&nbsp;{{MailRegion}}</span>
                        <span>&nbsp;{{MailPostalCode}}</span></div>
                      <div class="address-block__row">{{MailCountry}}</div>
                    </div>
                    <div class="actions">
                      <div class="actions">
                        <v-btn small outline color="blue" @click="editAddress1">Change</v-btn>
                      </div>
                    </div>
                  </div>
                </v-expand-transition>
                 <v-expand-transition>
                  <div class="form active" v-show="focusAddress1">
                    <h4>Change Delivery Address</h4>
                    <!--
                    <v-alert type="primary" :value="true">
                      Changing Registered Office Addresses is an additional fee.
                    </v-alert>
                    -->
                    <div class="form__row">
                      <v-text-field box label="New Delivery Address"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Address 1" v-model="MailStreet1"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Address 2" v-model="MailStreet2"></v-text-field>
                    </div>
                    <div class="form__row test">
                      <v-text-field box label="City" v-model="MailCity"></v-text-field>
                      <v-select box label="Province" :items="Regions" v-model="MailRegion"></v-select>
                      <v-text-field box label="Postal Code" v-model="MailPostalCode"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Country" v-model="MailCountry"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-textarea box label="Special Instructions" v-model="MailSpecialInstructions"
                      ></v-textarea>
                    </div>
                    <div class="form__row form__btns">
                      <v-btn color="primary" @click="cancelEditAddress1">Update Address</v-btn>
                      <v-btn @click="cancelEditAddress1">Cancel</v-btn>
                    </div>
                  </div>
                </v-expand-transition>
              </li>
            </ul>
          </v-card>
          <v-card v-bind:class="{ focused: focusAddress2 }">
            <ul>
              <li class="container">
                <v-expand-transition>
                  <div class="meta-container" v-show="!focusAddress2">
                    <label>Mailing Address</label>
                    <div class="value">
                      <div class="address-block__row">{{MailStreet1}}</div>
                      <div class="address-block__row">
                        <span>{{MailCity}}</span>
                        <span>&nbsp;{{MailRegion}}</span>
                        <span>&nbsp;{{MailPostalCode}}</span></div>
                      <div class="address-block__row">{{MailCountry}}</div>
                    </div>
                    <div class="actions">
                      <div class="actions">
                        <v-btn small outline color="blue" @click="editAddress2">Change</v-btn>
                      </div>
                    </div>
                  </div>
                </v-expand-transition>
                <v-expand-transition>
                  <div class="form active" v-show="focusAddress2">
                    <h4>Change Mailing Address</h4>
                    <!--
                    <v-alert type="primary" :value="true">
                      Changing Registered Office Addresses is an additional fee.
                    </v-alert>
                    -->
                    <div class="form__row">
                      <v-checkbox label="Same as Delivery Address"></v-checkbox>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="New Delivery Address"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Address 1" v-model="MailStreet1"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Address 2" v-model="MailStreet2"></v-text-field>
                    </div>
                    <div class="form__row test">
                      <v-text-field box label="City" v-model="MailCity"></v-text-field>
                      <v-select box label="Province" :items="Regions" v-model="MailRegion"></v-select>
                      <v-text-field box label="Postal Code" v-model="MailPostalCode"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-text-field box label="Country" v-model="MailCountry"></v-text-field>
                    </div>
                    <div class="form__row">
                      <v-textarea box label="Special Instructions" v-model="MailSpecialInstructions"
                      ></v-textarea>
                    </div>
                    <div class="form__row form__btns">
                      <v-btn color="primary" @click="cancelEditAddress2">Update Address</v-btn>
                      <v-btn @click="cancelEditAddress2">Cancel</v-btn>
                    </div>
                  </div>
                </v-expand-transition>
              </li>
            </ul>
          </v-card>
        </section>
        <section class="edit-focus">
          <header>
            <h2>2. Registered Office Addresses (Dialog)</h2>
            <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium</p>
          </header>
          <v-card>
            <AddressList2/>
          </v-card>
        </section>
        <!--
        <section>
          <h2>3. Director Information</h2>
          <p>Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium</p>
          <v-card>
            <DirectorList/>
          </v-card>
        </section>
        <section>
          <h2 class="mb-3">5. Certification</h2>
          <v-card>
            <Certification />
          </v-card>
        </section>
        -->
      </article>
      <aside>
        <affix relative-element-selector="#example-content" :offset="{ top: 120, bottom: 40 }">
          <FeeSummary/>
        </affix>
      </aside>
    </v-container>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { Affix } from 'vue-affix'
import EntityInfo from '@/components/EntityInfo.vue'
import ARFilingDates from '@/components/ARFilingDates.vue'
import AddressList from '@/components/AddressList.vue'
import AddressList2 from '@/components/AddressList2.vue'
import DirectorList from '@/components/DirectorList.vue'
import EditAddress from '@/components/EditAddress.vue'
import FeeSummary from '@/components/FeeSummary.vue'
import Certification from '@/components/Certification.vue'
import Delivery from '@/components/Delivery.vue'

export default {
  name: 'AnnualReport',
  components: {
    Affix,
    EntityInfo,
    ARFilingDates,
    AddressList,
    AddressList2,
    DirectorList,
    EditAddress,
    FeeSummary,
    Certification,
    Delivery
  },

  data() {
    return {
      Regions: [
        'British Columbia'
      ],
      isEditing: false,
      focusAddress1: false,
      focusAddress2: false,
      MailStreet1: "1234 Main Street",
      MailStreet2: "",
      MailCity: "Victoria",
      MailRegion: "BC",
      MailPostalCode: "V9A 2G8",
      MailCountry: "Canada",
      MailSpecialInstructions: "Up the driveway and the go to the garden suite out back. Don't worry about the pit-bull, he's harmless."
    };
  },

  methods: {
    editAddress1: function () {
      this.isEditing = true
      this.focusAddress1 = true
      this.focusAddress2 = false
    },
    cancelEditAddress1: function () {
      this.isEditing = false
      this.focusAddress1 = false
    },
    editAddress2: function () {
      this.isEditing = true
      this.focusAddress2 = true
      this.focusAddress1 = false
    },
    cancelEditAddress2: function () {
      this.isEditing = false
      this.focusAddress2 = false
    },
  }
}
</script>

<style lang="stylus">
  @import "../assets/styles/theme.styl"

  // Page Layout
  .view-container
    display flex
    flex-flow row nowrap
    padding-top 3rem
    padding-bottom 3rem

    article
      flex 1 1 auto

      section
        margin-top 3rem

    aside
      flex 0 0 auto
      width 20rem
      margin-top 3rem

      .affix
        width 20rem

    section
      > p
        color $gray6
        font-size 0.875rem

  @media (min-width 960px)
    .view-container
      article
        margin-right 2rem

      aside
        margin-top 0

  // Page Contents
  h1
    margin-bottom 1.25rem
    line-height 2rem
    letter-spacing -0.01rem
    font-size 2rem
    font-weight 500

  h2
    margin-bottom 0.25rem
    font-size 1.125rem
    font-weight 500

  p
    margin-bottom 1rem
    color $gray7

  ul
    margin 0
    padding 0
    list-style-type none

  article
    .v-card
      line-height 1.2rem
      font-size 0.875rem

      li
        .meta-container
          display flex

          > label:first-child
            flex 0 0 auto
            padding-right: 4rem
            width 12rem

          .value
            flex 1 1 auto

      li + li
        border-top 1px solid $gray3

    .v-btn
      min-width 4rem
      text-transform none

  .form-buttons
    margin-top 3rem
    pading-bottom 2rem
    text-align right

    .v-btn
      margin 0

      + .v-btn
        margin-left 0.5rem

  .v-input
    margin-top 0

  .editing header
  .editing section .v-card
    transition all ease-out 0.2s;

  .editing
    header,
    .v-card
      opacity 0.3

    .v-card.focused
      opacity 1

  .form__row + .form-row
    margin-top 1.5rem

  .form__btns
    text-align right

    .v-btn
      margin 0

    .v-btn + .v-btn
      margin-left 0.5rem

  h4
    margin-top 0.5rem
    margin-bottom 1.5rem
    font-size 1.125rem
    font-weight 500

  .v-alert
    margin-bottom 1.5rem

  .form__row.test
    margin-left -0.5rem
    margin-right -0.5rem
    display flex

    .v-input
      flex 1 1 auto
      margin 0 0.5rem


</style>

