<template>
  <v-dialog v-model="dialog" width="45rem">
    <v-card>
      <v-card-title>Unable to Download Document</v-card-title>

      <v-card-text>
        <p class="genErr">We were unable to download your filing history document(s).</p>

        <template v-if="!isRoleStaff">
          <p class="genErr">If this error persists, please contact us.</p>
          <ErrorContact />
        </template>
      </v-card-text>

      <v-divider class="my-0"></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="close()">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import { mapGetters } from 'vuex'
import ErrorContact from '@/components/ErrorContact.vue'

@Component({
  computed: {
    // Property definition for runtime environment.
    ...mapGetters(['isRoleStaff'])
  },
  components: { ErrorContact }
})
export default class DownloadErrorDialog extends Vue {
  // Getter definition for static type checking.
  readonly isRoleStaff!: boolean

  // Prop to display the dialog.
  @Prop() private dialog: boolean

  // Pass click event to parent.
  @Emit() private close () { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';
</style>
