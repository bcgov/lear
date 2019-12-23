<template>
  <v-menu
    v-model="menu"
    :close-on-content-click="false"
    :nudge-width="200"
    offset-y
    max-width="18rem"
  >
    <template v-slot:activator="{ on }">
      <span v-on="on">
        <v-icon>mdi-information-outline</v-icon>Minimum three directors required
      </span>
    </template>
    <v-card>
      <v-list-item>
        <v-list-item-content>
          A minimum of three directors are required, to be in compliance with the Cooperative
          Association Act (Section xx).You can continue your filing, but you must become
          compliant with the Cooperative Association Act as soon as possible.
        </v-list-item-content>
      </v-list-item>
    </v-card>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue, Prop, Emit } from 'vue-property-decorator'

@Component({})
export default class WarningPopover extends Vue {

}
</script>
