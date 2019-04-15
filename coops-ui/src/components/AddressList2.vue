<template>
  <ul class="address-list">
    <li class="container">
      <div class="meta-container">
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
      <v-dialog class="edit-address-dialog" width="50rem" v-model="editAddress1">
        <v-card>
          <v-card-title>
            Update Delivery Address
          </v-card-title>
          <v-card-text>
            <div class="form active">
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
                <v-btn color="primary" @click="cancelEditAddress1">Update Address</v-btn>
                <v-btn @click="cancelEditAddress2">Cancel</v-btn>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>
    </li>
    <li class="container">
      <div class="meta-container">
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
      <v-dialog class="edit-address-dialog" width="50rem" v-model="editAddress2">
        <v-card>
          <v-card-title>
            Update Mailing Address
          </v-card-title>
          <v-card-text>
            <div class="form">
              <div class="form__row">
                <v-checkbox label="Same as Delivery Address"></v-checkbox>
              </div>
              <div class="form__row">
                <v-text-field box label="Address Line 1"></v-text-field>
              </div>
              <div class="form__row">
                <v-text-field box label="Address Line 2"></v-text-field>
              </div>
              <div class="form__row form__btns">
                <v-btn color="primary" @click="cancelEditAddress1">Update Mailing Address</v-btn>
                <v-btn @click="cancelEditAddress2">Cancel</v-btn>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>
    </li>
  </ul>
</template>

<script>
export default {
  name: 'AddressList2',

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
    },

    cancelEditAddress1: function () {
      this.editAddress1 = false
    },

    showEditAddress2: function () {
      this.editAddress2 = true
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

// Passcode Dialog
.v-dialog
  margin 2rem

.v-card__title
  padding 1.25rem 1.5rem
  color #ffffff
  background $BCgovBlue5
  font-size 1rem
  font-weight 400

.v-card__text
  padding 1.5rem
  font-weight 300

</style>