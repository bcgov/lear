<template>
  <v-data-table
    :headers="headers"
    :items="filedItems"
    :expand="expand"
    item-key="name"
    hide-actions
  >
    <template v-slot:items="props">
      <tr @click="props.expanded = !props.expanded">
        <td><strong>{{ props.item.name }}</strong></td>
        <td>{{ props.item.status }}</td>
        <td>{{ props.item.price }}</td>
      </tr>
    </template>
    <template v-slot:expand="props">
      <v-container style="background-color: #f7f8fa;">
        <v-btn flat small color="primary"><v-icon>attachment</v-icon><span>Annual Report</span></v-btn>
        <v-btn flat small color="primary"><v-icon>attachment</v-icon><span>Registered Office Change</span></v-btn>
        <v-btn flat small color="primary"><v-icon>attachment</v-icon><span>Director Change</span></v-btn>
        <v-btn flat small color="primary"><v-icon>attachment</v-icon><span>Receipt</span></v-btn>
        <v-btn small color="primary">Download</v-btn>
      </v-container>
    </template>
  </v-data-table>
</template>

<script lang="ts">
  export default {
    name: 'FeeSummary',

    data () {
      return {
        expand: true,
        headers: [
          { text: 'Name', align: 'left', sortable: false, value: 'name'},
          { text: 'Status', sortable: false, value: 'status' },
          { text: 'Price (CDN)', sortable: false, value: 'price' }
        ],

        filedItems: [
          { name: 'Annual Report (2019)', status: 'Completed', price: '$70.00', enabled: false },
          { name: 'Annual Report (2018)', status: 'Completed', price: '$70.00', enabled: false }
        ]
      }
    }
  }
</script>