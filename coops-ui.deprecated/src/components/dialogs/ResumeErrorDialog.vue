<template>
  <v-dialog v-model="dialog" width="45rem" persistent :attach="attach" content-class="resume-error-dialog">
    <v-card>
      <v-card-title>Unable to Resume Filing</v-card-title>

      <v-card-text>
        <p class="genErr">We were unable to resume your filing. You can return to
          the Business Dashboard and try again.</p>

        <template v-if="!isRoleStaff">
          <p class="genErr">If this error persists, please contact us.</p>
          <ErrorContact />
        </template>
      </v-card-text>

      <v-divider class="my-0"></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn id="dialog-exit-button" color="primary" text @click="exit()">Return to dashboard</v-btn>
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
export default class ResumeErrorDialog extends Vue {
  // Getter definition for static type checking.
  readonly isRoleStaff!: boolean

  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Prop to provide attachment selector.
  @Prop() private attach: string

  // Pass click event to parent.
  @Emit() private exit () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
