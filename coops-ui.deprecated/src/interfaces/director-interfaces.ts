import Vue from 'vue'

export interface Director extends Vue {
  actions?: string[];
  isDirectorActionable?: boolean;
}
