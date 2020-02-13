<template>
  <v-dialog v-model="dialog" width="45rem" persistent :attach="attach" content-class="delete-error-dialog">
      <v-card>
        <v-card-title id="dialog-title" v-if="errors.length > 0 || warnings.length < 1">
          Unable to Delete Filing
        </v-card-title>
        <v-card-title id="dialog-title" v-else>
          Filing Deleted with Warnings
        </v-card-title>

        <v-card-text id="dialog-text">
          <p class="genErr" v-if="errors.length + warnings.length < 1">
            We were unable to delete your filing.
          </p>
          <p class="genErr" v-else-if="errors.length > 0">
            We were unable to delete your filing due to the following errors:
          </p>
          <p class="genErr" v-else>
            Please note the following:
          </p>
          <p class="genErr" v-for="(error, index) in errors" :key="index">
            {{error.error}}
          </p>
          <p class="genErr" v-for="(warning, index) in warnings" :key="index">
            {{warning.warning}}
          </p>
          <template v-if="!isRoleStaff">
            <p class="genErr">If you need help, please contact us.</p>
            <ErrorContact class="mt-5" />
          </template>
        </v-card-text>

        <v-divider class="my-0"></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn id="dialog-ok-btn" color="primary" text @click="okay()">OK</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import { mapGetters } from 'vuex'
import { ErrorContact } from '@/components/common'

@Component({
  computed: {
    // Property definition for runtime environment.
    ...mapGetters(['isRoleStaff'])
  },
  components: { ErrorContact }
})
export default class DeleteErrorDialog extends Vue {
  // Getter definition for static type checking.
  readonly isRoleStaff!: boolean

  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to provide attachment selector.
  @Prop() private attach: string

  // Prop containing error messages.
  @Prop() private errors: object[]

  // Prop containing warning messages.
  @Prop() private warnings: object[]

  // Pass click event to parent.
  @Emit() private okay () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
