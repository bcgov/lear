<template>
  <v-menu v-if="dialogObj != null"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-y
    max-width="18rem"
  >
    <template v-slot:activator="{ on }">
      <span v-on="on">
        <v-icon  style="vertical-align: bottom">mdi-information-outline</v-icon>{{ dialogObj.title }}
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

@Component({})
export default class WarningPopover extends Vue {
@Prop({ default: null })
private dialogObj: any
}
</script>
