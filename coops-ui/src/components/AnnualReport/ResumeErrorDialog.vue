<template>
  <v-dialog v-model="dialog" width="45rem" persistent>
    <v-card>
      <v-card-title>Unable to Resume Filing</v-card-title>
      <v-card-text>
        <p class="genErr">We were unable to resume your filing. You can return to your dashboard
          and try again.</p>
        <p class="genErr">If this error persists, please contact us.</p>

        <ErrorContact />

      </v-card-text>
      <v-divider class="my-0"></v-divider>
      <v-card-actions>
        <v-btn color="primary" text @click="exit()">Return to dashboard</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import ErrorContact from '@/components/ErrorContact.vue'

@Component({
  components: { ErrorContact }
})
export default class ResumeErrorDialog extends Vue {
  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Pass click event to parent.
  @Emit() private exit () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
