<template>
  <ul class="address-list">
    <li class="container">
      <v-expand-transition>
        <div class="form" v-bind:class="{ active: editAddress1 }"  v-show="editAddress1">
          <h4>Update Delivery Address</h4>
          <div class="form__row">
            <v-text-field box label="Start typing an address"></v-text-field>
          </div>
          <div class="form__row">
            <v-text-field box label="Start typing an address"></v-text-field>
          </div>
          <div class="form__row">
            <v-text-field box label="Special Instructions"></v-text-field>
          </div>
          <div class="form__row form__btns">
            <v-btn color="primary" @click="cancelEditAddress1">Save</v-btn>
            <v-btn @click="cancelEditAddress1">Cancel</v-btn>
          </div>
        </div>
      </v-expand-transition>
      <v-expand-transition>
        <div class="meta-container" v-show="!editAddress1">
          <label>Delivery Address</label>
          <div class="value">
            <div class="address-block__row">{{MailStreet}}</div>
            <div class="address-block__row">
              <span>{{MailCity}}</span>
              <span>&nbsp;{{MailRegion}}</span>
              <span>&nbsp;{{MailPostalCode}}</span></div>
            <div class="address-block__row">{{MailCountry}}</div>
          </div>
          <div class="actions">
            <div class="actions">
              <v-btn small outline color="blue" @click="showEditAddress1">Change</v-btn>
            </div>
          </div>
        </div>
      </v-expand-transition>
    </li>
    <li class="container">
      <v-expand-transition>
        <div class="form" v-bind:class="{ active: editAddress2 }"  v-show="editAddress2">
          <h4>Update Mailing Address</h4>
          <div class="form__row">
            <v-text-field box label="Enter Information"></v-text-field>
          </div>
          <div class="form__row">
            <v-text-field box label="Enter Information"></v-text-field>
          </div>
          <div class="form__row form__btns">
            <v-btn color="primary" @click="cancelEditAddress1">Update Mailing Address</v-btn>
            <v-btn @click="cancelEditAddress2">Cancel</v-btn>
          </div>
        </div>
      </v-expand-transition>
      <v-expand-transition>
        <div class="meta-container" v-show="!editAddress2">
          <label>Mailing Address</label>
          <div class="value">
            <div class="address-block__row">{{MailStreet}}</div>
            <div class="address-block__row">
              <span>{{MailCity}}</span>
              <span>&nbsp;{{MailRegion}}</span>
              <span>&nbsp;{{MailPostalCode}}</span></div>
            <div class="address-block__row">{{MailCountry}}</div>
          </div>
          <div class="actions">
            <div class="actions">
              <v-btn small outline color="blue" @click="showEditAddress2">Change</v-btn>
            </div>
          </div>
        </div>
      </v-expand-transition>
    </li>
  </ul>
</template>

<script>
export default {
  name: 'AddressList',

  data: () => ({
    editAddress1: false,
    editAddress2: false,
    MailStreet: "1234 Main Street",
    MailCity: "Victoria",
    MailRegion: "BC",
    MailPostalCode: "V9A 2G8",
    MailCountry: "Canada",
    DeliveryStreet: "1234 Main Street",
    DeliveryCity: "Victoria",
    DeliveryRegion: "BC",
    DeliveryPostalCode: "V9A 2G8",
    DeliveryCountry: "Canada"
  }),

  methods: {
    showEditAddress1: function () {
      this.editAddress1 = true
      this.editAddress2 = false
    },

    cancelEditAddress1: function () {
      this.editAddress1 = false
    },

    showEditAddress2: function () {
      this.editAddress2 = true
      this.editAddress1 = false
    },

    cancelEditAddress2: function () {
      this.editAddress2 = false
    }
  }
}
</script>

<style lang="stylus" scoped>
  @import "../assets/styles/theme.styl"

  h4
    margin-bottom 1.5rem

  .form__row + .form-row
    margin-top 1.5rem

  .form__btns
    text-align right

    .v-btn
      margin 0

    .v-btn + .v-btn
      margin-left 0.5rem

</style>