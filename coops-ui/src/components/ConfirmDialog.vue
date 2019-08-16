<template>
  <v-dialog v-model="dialog"
    :max-width="options.width"
    :style="{ zIndex: options.zIndex }"
    :persistent="options.persistent"
    @keydown.esc="onClickCancel">

    <v-card>
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text v-show="!!message">{{ message }}</v-card-text>
      <v-divider class="my-0" v-show="!!options.yes || !!options.no || !!options.cancel"></v-divider>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" flat v-show="!!options.yes" @click.native="onClickYes">
          {{ options.yes }}
        </v-btn>
        <v-btn color="primary" flat v-show="!!options.no" @click.native="onClickNo">
          {{ options.no }}
        </v-btn>
        <v-btn color="secondary" flat v-show="!!options.cancel" @click.native="onClickCancel">
          {{ options.cancel }}
        </v-btn>
      </v-card-actions>
    </v-card>

  </v-dialog>
</template>

<script>
/**
 * Vuetify Confirm Dialog component
 * ref: https://gist.github.com/eolant/ba0f8a5c9135d1a146e1db575276177d
 *
 * Insert component where you want to use it:
 * <confirm ref="confirm"></confirm>
 *
 * Call it using promise:
 * this.$refs.confirm.open('Delete', 'Are you sure?', { color: 'red' }).then((confirm) => {})
 *
 * Or use await:
 * if (await this.$refs.confirm.open('Delete', 'Are you sure?', { color: 'red' })) {
 *   // yes
 * }
 * else {
 *   // cancel
 * }
 *
 * Alternatively you can place it in main App component and access it globally via this.$root.$confirm
 * <template>
 *   <v-app>
 *     ...
 *     <confirm ref="confirm"></confirm>
 *   </v-app>
 * </template>
 *
 * mounted() {
 *   this.$root.$confirm = this.$refs.confirm.open
 * }
 */
export default {
  name: 'ConfirmDialog',

  data: () => ({
    dialog: false,
    resolve: null,
    reject: null,
    message: null,
    title: null,
    options: {
      width: 300,
      zIndex: 200,
      persistent: false,
      yes: 'Yes',
      no: 'No',
      cancel: 'Cancel'
    }
  }),

  methods: {
    open (title, message, options) {
      this.dialog = true
      this.title = title
      this.message = message
      this.options = Object.assign(this.options, options)
      return new Promise((resolve, reject) => {
        this.resolve = resolve
        this.reject = reject
      })
    },
    onClickYes () {
      this.resolve(true)
      this.dialog = false
    },
    onClickNo () {
      this.resolve(false)
      this.dialog = false
    },
    onClickCancel () {
      this.reject()
      this.dialog = false
    }
  }
}
</script>
