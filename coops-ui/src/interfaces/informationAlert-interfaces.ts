import Vue from 'vue'

export interface AlertMessage extends Vue {
  title: String
  msg: String
  additionalItems: Array<String>
}
