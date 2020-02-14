<template>
  <v-card flat id="detail-comment-container">
    <v-textarea
      outlined
      auto-grow
      rows="5"
      id="detail-comment-textfield"
      :counter="MAXLENGTH"
      :value="comment"
      :rules="rules"
      @input="emitComment($event)"
    />
  </v-card>
</template>

<script lang="ts">
import { Component, Vue, Prop, Watch, Emit } from 'vue-property-decorator'

@Component({})
export default class DetailComment extends Vue {
  private readonly MAXLENGTH = 4096

  /**
   * Array of validations rules for the Comment textarea.
   */
  private get rules (): Array<Function> {
    // exclude whitespace in minimum length check
    // include whitespace in maximum length check
    return [
      val => (val && val.trim().length > 0) || 'Detail Comment is required.',
      val => (val.length <= this.MAXLENGTH) || 'Maximum characters exceeded.'
    ]
  }

  /**
   * Comment passed into this component.
   */
  @Prop({ default: '' })
  private comment: string

  /**
   * Called when prop changes (ie, is updated via parent).
   */
  @Watch('comment')
  private onCommentChanged (val: string): void {
    const isValidComment = this.rules.every(rule => rule(val) === true)
    this.emitValid(isValidComment)
  }

  /**
   * Emits an update event with the changed comment.
   */
  @Emit('update:comment')
  private emitComment (val: string): void { }

  /**
   * Emits an event indicating whether or not this component is valid.
   */
  @Emit('valid')
  private emitValid (val: boolean): void { }
}
</script>

<style lang="scss" scoped>
// @import '@/assets/styles/theme.scss';

#detail-comment-container {
  line-height: 1.2rem;
  font-size: 0.875rem;
}
</style>
