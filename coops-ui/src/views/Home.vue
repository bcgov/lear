<template>
  <div class="home">
    <Tombstone/>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import Tombstone from '@/components/Tombstone.vue'

@Component({
  components: {
    Tombstone
  }
})
export default class Home extends Vue {}
</script>
