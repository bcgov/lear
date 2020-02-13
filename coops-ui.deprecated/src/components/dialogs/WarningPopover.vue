<template>
  <v-menu v-if="dialogObj != null"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-y
    max-width="18rem"
  >
    <template v-slot:activator="{ on }">
      <span class="warning-text" v-on="on">
        <v-icon class="warning-icon">mdi-information-outline</v-icon>{{ dialogObj.title }}
      </span>
    </template>
    <v-card>
      <v-list-item>
        <v-list-item-content>
         {{ dialogObj.msg }}
        </v-list-item-content>
      </v-list-item>
    </v-card>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'
import { AlertMessageIF } from '@/interfaces'

@Component({})
export default class WarningPopover extends Vue {
  @Prop({ default: null })
  private dialogObj: AlertMessageIF
}
</script>

<style lang="scss">
@import '@/assets/styles/theme.scss';
.warning-text {
  font-weight: bold;
  font-size: 0.9rem;
  color: $BCgovIconBlue;

  .v-icon {
    vertical-align: bottom !important;
    color: $BCgovIconBlue !important;
  }

}
</style>
