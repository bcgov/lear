import Vue from 'vue'
import Vuelidate from 'vuelidate'
import Vuetify from 'vuetify'
import store from '@/store/store'

import { SummaryOfficeAddresses } from '@/components/common'

import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('OfficeAddresses as a BCOMP', () => {
  let vm

  beforeAll(() => {
    // init store
    store.state.entityType = EntityTypes.BCOMP
    store.state.registeredAddress = {
      deliveryAddress: {
        addressCity: 'delCity',
        addressCountry: 'delCountry',
        addressRegion: 'delRegion',
        deliveryInstructions: 'delInstructions',
        postalCode: 'delPostal',
        streetAddress: 'delStreet',
        streetAddressAdditional: 'delStreetAdd'
      },
      mailingAddress: {
        addressCity: 'mailCity',
        addressCountry: 'mailCountry',
        addressRegion: 'mailRegion',
        deliveryInstructions: 'mailInstructions',
        postalCode: 'mailPostal',
        streetAddress: 'mailStreet',
        streetAddressAdditional: 'mailStreetAdd'
      }
    }

    store.state.recordsAddress = {
      deliveryAddress: {
        addressCity: 'recDelCity',
        addressCountry: 'recDelCountry',
        addressRegion: 'recDelRegion',
        deliveryInstructions: 'recDelInstructions',
        postalCode: 'recDelPostal',
        streetAddress: 'recDelStreet',
        streetAddressAdditional: 'recDelStreetAdd'
      },
      mailingAddress: {
        addressCity: 'recMailCity',
        addressCountry: 'recMailCountry',
        addressRegion: 'recMailRegion',
        deliveryInstructions: 'recMailInstructions',
        postalCode: 'recMailPostal',
        streetAddress: 'recMailStreet',
        streetAddressAdditional: 'recMailStreetAdd'
      }
    }
  })

  it('loads the current office addresses properly', async () => {
    const Constructor = Vue.extend(SummaryOfficeAddresses)
    const instance = await new Constructor({
      propsData: {
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.recordsAddress
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify the `same as above text is not displayed
    expect(vm.$el.querySelector('#sameAsAbove')).toBeNull()

    // Verify the `same as registered` text is not displayed
    expect(vm.$el.querySelector('#sameAsRegistered')).toBeNull()

    const deliveryAddress = vm.registeredAddress.deliveryAddress
    expect(deliveryAddress['streetAddress']).toEqual('delStreet')
    expect(deliveryAddress['streetAddressAdditional']).toEqual('delStreetAdd')
    expect(deliveryAddress['addressCity']).toEqual('delCity')
    expect(deliveryAddress['addressRegion']).toEqual('delRegion')
    expect(deliveryAddress['postalCode']).toEqual('delPostal')
    expect(deliveryAddress['addressCountry']).toEqual('delCountry')
    expect(deliveryAddress['deliveryInstructions']).toEqual('delInstructions')

    const mailingAddress = vm.registeredAddress.mailingAddress
    expect(mailingAddress['streetAddress']).toEqual('mailStreet')
    expect(mailingAddress['streetAddressAdditional']).toEqual('mailStreetAdd')
    expect(mailingAddress['addressCity']).toEqual('mailCity')
    expect(mailingAddress['addressRegion']).toEqual('mailRegion')
    expect(mailingAddress['postalCode']).toEqual('mailPostal')
    expect(mailingAddress['addressCountry']).toEqual('mailCountry')
    expect(mailingAddress['deliveryInstructions']).toEqual('mailInstructions')

    const recDeliveryAddress = vm.recordsAddress.deliveryAddress
    expect(recDeliveryAddress['streetAddress']).toEqual('recDelStreet')
    expect(recDeliveryAddress['streetAddressAdditional']).toEqual('recDelStreetAdd')
    expect(recDeliveryAddress['addressCity']).toEqual('recDelCity')
    expect(recDeliveryAddress['addressRegion']).toEqual('recDelRegion')
    expect(recDeliveryAddress['postalCode']).toEqual('recDelPostal')
    expect(recDeliveryAddress['addressCountry']).toEqual('recDelCountry')
    expect(recDeliveryAddress['deliveryInstructions']).toEqual('recDelInstructions')

    const recMailingAddress = vm.recordsAddress.mailingAddress
    expect(recMailingAddress['streetAddress']).toEqual('recMailStreet')
    expect(recMailingAddress['streetAddressAdditional']).toEqual('recMailStreetAdd')
    expect(recMailingAddress['addressCity']).toEqual('recMailCity')
    expect(recMailingAddress['addressRegion']).toEqual('recMailRegion')
    expect(recMailingAddress['postalCode']).toEqual('recMailPostal')
    expect(recMailingAddress['addressCountry']).toEqual('recMailCountry')
    expect(recMailingAddress['deliveryInstructions']).toEqual('recMailInstructions')
  })

  it('displays the `same as registered` text when records and registered addresses match', async () => {
    const recordsAddress = {
      deliveryAddress: {
        addressCity: 'delCity',
        addressCountry: 'delCountry',
        addressRegion: 'delRegion',
        deliveryInstructions: 'delInstructions',
        postalCode: 'delPostal',
        streetAddress: 'delStreet',
        streetAddressAdditional: 'delStreetAdd'
      },
      mailingAddress: {
        addressCity: 'mailCity',
        addressCountry: 'mailCountry',
        addressRegion: 'mailRegion',
        deliveryInstructions: 'mailInstructions',
        postalCode: 'mailPostal',
        streetAddress: 'mailStreet',
        streetAddressAdditional: 'mailStreetAdd'
      }
    }

    const Constructor = Vue.extend(SummaryOfficeAddresses)
    const instance = await new Constructor({
      propsData: {
        registeredAddress: store.state.registeredAddress,
        recordsAddress: recordsAddress
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify the `same as above text is not displayed
    expect(vm.$el.querySelector('#sameAsAbove')).toBeNull()

    // Verify the `same as registered` text is not displayed
    expect(vm.$el.querySelector('#sameAsRegistered').textContent).toContain('Same as Registered Office')

    const deliveryAddress = vm.registeredAddress.deliveryAddress
    expect(deliveryAddress['streetAddress']).toEqual('delStreet')
    expect(deliveryAddress['streetAddressAdditional']).toEqual('delStreetAdd')
    expect(deliveryAddress['addressCity']).toEqual('delCity')
    expect(deliveryAddress['addressRegion']).toEqual('delRegion')
    expect(deliveryAddress['postalCode']).toEqual('delPostal')
    expect(deliveryAddress['addressCountry']).toEqual('delCountry')
    expect(deliveryAddress['deliveryInstructions']).toEqual('delInstructions')

    const mailingAddress = vm.registeredAddress.mailingAddress
    expect(mailingAddress['streetAddress']).toEqual('mailStreet')
    expect(mailingAddress['streetAddressAdditional']).toEqual('mailStreetAdd')
    expect(mailingAddress['addressCity']).toEqual('mailCity')
    expect(mailingAddress['addressRegion']).toEqual('mailRegion')
    expect(mailingAddress['postalCode']).toEqual('mailPostal')
    expect(mailingAddress['addressCountry']).toEqual('mailCountry')
    expect(mailingAddress['deliveryInstructions']).toEqual('mailInstructions')

    expect(vm.recordsAddress).toEqual(vm.registeredAddress)
  })
})
