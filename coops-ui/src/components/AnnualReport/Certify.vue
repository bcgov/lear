<template>
  <v-card flat id="AR-step-4-container">
    <div class="container">
      <div class="certifiedby-container">
        <label>
          <span>Legal Name</span>
        </label>
        <div class="value certifiedby">
          <v-text-field
            id="certified-by-textfield"
            v-model="certifyTextField"
            label="Name of current director, officer, or lawyer of the association"
            box
          />
        </div>
      </div>
      <v-checkbox v-model="certifyCheckbox">
        <template slot="label">
          <div class="certify-stmt">
            I, <b>{{trimmedCertifiedTextField || '[Legal Name]'}}</b>, certify that I have relevant knowledge of the
            association and that I am authorized to make this filing.
          </div>
        </template>
      </v-checkbox>
      <p class="certify-clause">{{currentDate}}</p>
      <p class="certify-clause">
        Note: It is an offence to make a false or misleading statement in
        respect of a material fact in a record submitted to the Corporate Registry for filing.
        See section 200 of the Cooperatives Association Act.
      </p>
    </div>
  </v-card>
</template>

<script>
import { mapState } from 'vuex'

export default {
  name: 'Certify',

  props: {
    certifiedBy: String,
    isCertified: Boolean
  },

  data () {
    return {
      certifyTextField: '',
      certifyCheckbox: false
    }
  },

  computed: {
    ...mapState(['currentDate']),

    trimmedCertifiedTextField () /* string */ {
      return this.certifyTextField && this.certifyTextField.trim()
    },

    isCertifyValid () /* boolean */ {
      return !!(this.certifyCheckbox && this.trimmedCertifiedTextField)
    }
  },

  watch: {
    certifiedBy (val) {
      this.certifyTextField = val
    },

    isCertified (val) {
      this.certifyCheckbox = val
    },

    trimmedCertifiedTextField: function (val) {
      this.$emit('update:certifiedBy', val)
    },

    isCertifyValid: function (val) {
      this.$emit('update:isCertified', val)
    }
  }
}
</script>

<style lang="stylus" scoped>
@import '../../assets/styles/theme.styl'

.certifiedby-container
  display flex
  flex-flow column nowrap
  position relative
  > label:first-child
    font-weight 500

@media (min-width 768px)
  .certifiedby-container
    flex-flow row nowrap
    > label:first-child
      flex 0 0 auto
      padding-right: 2rem
      width 12rem

.value.certifiedby
  min-width 35rem

.certify-clause
  padding-left 2rem
  color black
  font-size 0.875rem

.certify-stmt
  display:inline
  font-size: 0.875rem
  color black

#AR-step-4-container
  margin-top: 1rem;
  padding-bottom: 0.5rem;
  padding-top: 1rem;
  line-height: 1.2rem;
  font-size: 0.875rem;
</style>
