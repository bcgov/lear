import Vue from 'vue'

export interface FormType extends Vue {
  reset(): void
  validate(): boolean
}
