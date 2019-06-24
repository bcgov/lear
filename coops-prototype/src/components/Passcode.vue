<template>
  <div>
    <v-form class="passcode-form" ref="signInForm" v-model="signInFormValid">
      <h2>Sign in</h2>
      <div class="form__row">
        <v-text-field
          box
          label="Enter your Incorporation Number"
          append-icon="info"
          hint="Example: CP1234567"
          persistent-hint
          v-model="entityNum"
          :rules="entityNumRules"
        ></v-text-field>
      </div>
      <div class="form__row">
        <v-text-field
          box
          label="Enter your Passcode"
          append-icon="lock"
          hint="Example: 123456789"
          persistent-hint
          v-model="entityPasscode"
          :rules="entityPasscodeRules"
        ></v-text-field>
      </div>
      <div class="form__row form__btns">
        <v-btn class="recovery-btn" color="primary" flat large @click.stop="noPasscodeDialog = true">
          Don't have a Passcode?
        </v-btn>
        <v-btn class="sign-in-btn" color="primary" large to="/Dashboard" :disabled="!signInFormValid">
          Sign in
          <v-icon right>arrow_forward</v-icon>
        </v-btn>
      </div>
    </v-form>
    <v-dialog width="50rem" v-model="noPasscodeDialog">
      <v-card>
        <v-card-title>Don't have a Passcode?</v-card-title>
        <v-card-text>
          If you have not received, or have lost your Passcode, please contact us at:
          <ul class="contact-list">
            <li class="contact-list__row">
              <v-icon color="primary">phone</v-icon>
              <span class="contact-info__value">250 952-0568</span>
            </li>
            <li class="contact-list__row">
              <v-icon color="primary">email</v-icon>
              <span class="contact-info__value"><a v-bind:href="'mailto:SBC_ITOperationsSupport@gov.bc.ca'">SBC_ITOperationsSupport@gov.bc.ca</a></span>
            </li>
          </ul>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" flat
            @click="noPasscodeDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
export default {
  name: 'Passcode',

  data: () => ({
    entityPasscode: '',
    noPasscodeDialog: false,
    signInFormValid: false,
    entityNum: '',
    entityNumRules: [
      v => !!v || 'Incorporation Number is required'
    ],
    entityPasscodeRules: [
      v => !!v || 'Passcode is required',
      v => v.length >= 9 || 'Passcode must be exactly 9 digits'
    ]
  })
};
</script>

<style lang="stylus" scoped>
@import "../assets/styles/theme.styl"

h2
  margin-bottom 2rem
  font-size 1.5rem
  font-weight 500

.form__row + .form__row
  margin-top 1rem

.recovery-btn
  margin-right auto
  padding-right 0.7rem
  padding-left 0.7rem
  text-decoration underline
  font-size 1rem

.sign-in-btn
  font-weight 700

.v-input
  max-width 25rem

.passcode-form__alert-container
  margin-bottom 2rem

.v-alert
  margin 0

@media (max-width 600px)
  .form-btns
    flex-flow column nowrap

  .v-btn.recovery-btn
    order 1
    margin-top 0.5rem
    margin-left auto

  .v-btn.sign-in-btn
    width 100%

@media (min-width 960px)
  .v-btn.recovery-btn
    font-size 0.875rem

// Contact List
.contact-list
  margin-top 1.5rem
  padding 0
  font-weight 500
  list-style-type none

.contact-list__row
  overflow hidden
  white-space nowrap
  text-overflow ellipsis

.contact-list__row .v-icon
    vertical-align middle
    margin-top -0.2rem
    margin-right 1.25rem

.contact-list__row + .contact-list__row
  margin-top 0.5rem
</style>