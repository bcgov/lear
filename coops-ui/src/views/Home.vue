<template>
  <div class="home">
    <EntityInfo/>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import EntityInfo from '@/components/EntityInfo.vue'

@Component({
  components: {
    EntityInfo
  }
})
export default class Home extends Vue {}
</script>
