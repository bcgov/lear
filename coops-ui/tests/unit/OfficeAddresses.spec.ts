import Vue from 'vue'
import Vuelidate from 'vuelidate'
import Vuetify from 'vuetify'
import store from '@/store/store'

import { OfficeAddresses } from '@/components/Common'
import { mount, Wrapper } from '@vue/test-utils'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('OfficeAddresses', () => {
  let vm

  beforeAll(() => {
    // init store
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

  const draftAddresses = {
    registeredOffice: {
      deliveryAddress: {
        addressCity: 'delCityDraft',
        addressCountry: 'delCountryDraft',
        addressRegion: 'delRegionDraft',
        deliveryInstructions: 'delInstructionsDraft',w
        postalCode: 'delPostalDraft',
        streetAddress: 'delStreetDraft',
        streetAddressAdditional: 'delStreetAddDraft'
      },
      mailingAddress: {
        addressCity: 'mailCityDraft',
        addressCountry: 'mailCountryDraft',
        addressRegion: 'mailRegionDraft',
        deliveryInstructions: 'mailInstructionsDraft',
        postalCode: 'mailPostalDraft',
        streetAddress: 'mailStreetDraft',
        streetAddressAdditional: 'mailStreetAddDraft'
      }
    },
    recordsOffice: {
      deliveryAddress: {
        addressCity: 'recDelCityDraft',
        addressCountry: 'recDelCountryDraft',
        addressRegion: 'recDelRegionDraft',
        deliveryInstructions: 'recDelInstructionsDraft',
        postalCode: 'recDelPostalDraft',
        streetAddress: 'recDelStreetDraft',
        streetAddressAdditional: 'recDelStreetAddDraft'
      },
      mailingAddress: {
        addressCity: 'recMailCityDraft',
        addressCountry: 'recMailCountryDraft',
        addressRegion: 'recMailRegionDraft',
        deliveryInstructions: 'recMailInstructionsDraft',
        postalCode: 'recMailPostalDraft',
        streetAddress: 'recMailStreetDraft',
        streetAddressAdditional: 'recMailStreetAddDraft'
      }
    }
  }

  it('loads the current office addresses properly', async done => {
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.recordsAddress
      },
      vuetify
    })
    vm = instance.$mount()

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

    Vue.nextTick(() => {
      done()
    })
  })

  it('loads the current office addresses properly from a draft filing', async done => {
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        addresses: draftAddresses
      },
      vuetify
    })
    vm = instance.$mount()

    const deliveryAddress = vm.addresses.registeredOffice.deliveryAddress
    expect(deliveryAddress['streetAddress']).toEqual('delStreetDraft')
    expect(deliveryAddress['streetAddressAdditional']).toEqual('delStreetAddDraft')
    expect(deliveryAddress['addressCity']).toEqual('delCityDraft')
    expect(deliveryAddress['addressRegion']).toEqual('delRegionDraft')
    expect(deliveryAddress['postalCode']).toEqual('delPostalDraft')
    expect(deliveryAddress['addressCountry']).toEqual('delCountryDraft')
    expect(deliveryAddress['deliveryInstructions']).toEqual('delInstructionsDraft')

    const mailingAddress = vm.addresses.registeredOffice.mailingAddress
    expect(mailingAddress['streetAddress']).toEqual('mailStreetDraft')
    expect(mailingAddress['streetAddressAdditional']).toEqual('mailStreetAddDraft')
    expect(mailingAddress['addressCity']).toEqual('mailCityDraft')
    expect(mailingAddress['addressRegion']).toEqual('mailRegionDraft')
    expect(mailingAddress['postalCode']).toEqual('mailPostalDraft')
    expect(mailingAddress['addressCountry']).toEqual('mailCountryDraft')
    expect(mailingAddress['deliveryInstructions']).toEqual('mailInstructionsDraft')

    const recDeliveryAddress = vm.addresses.recordsOffice.deliveryAddress
    expect(recDeliveryAddress['streetAddress']).toEqual('recDelStreetDraft')
    expect(recDeliveryAddress['streetAddressAdditional']).toEqual('recDelStreetAddDraft')
    expect(recDeliveryAddress['addressCity']).toEqual('recDelCityDraft')
    expect(recDeliveryAddress['addressRegion']).toEqual('recDelRegionDraft')
    expect(recDeliveryAddress['postalCode']).toEqual('recDelPostalDraft')
    expect(recDeliveryAddress['addressCountry']).toEqual('recDelCountryDraft')
    expect(recDeliveryAddress['deliveryInstructions']).toEqual('recDelInstructionsDraft')

    const recMailingAddress = vm.addresses.recordsOffice.mailingAddress
    expect(recMailingAddress['streetAddress']).toEqual('recMailStreetDraft')
    expect(recMailingAddress['streetAddressAdditional']).toEqual('recMailStreetAddDraft')
    expect(recMailingAddress['addressCity']).toEqual('recMailCityDraft')
    expect(recMailingAddress['addressRegion']).toEqual('recMailRegionDraft')
    expect(recMailingAddress['postalCode']).toEqual('recMailPostalDraft')
    expect(recMailingAddress['addressCountry']).toEqual('recMailCountryDraft')
    expect(recMailingAddress['deliveryInstructions']).toEqual('recMailInstructionsDraft')

    Vue.nextTick(() => {
      done()
    })
  })

  it('has enabled Change button', done => {
    const wrapper: Wrapper<OfficeAddresses> = mount(OfficeAddresses, {
      sync: false,
      propsData: { changeButtonDisabled: false,
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.recordsAddress
      },
      vuetify
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeUndefined()

    Vue.nextTick(() => {
      done()
    })
  })

  it('has enabled Change button', done => {
    const wrapper: Wrapper<OfficeAddresses> = mount(OfficeAddresses, {
      sync: false,
      propsData: { changeButtonDisabled: true,
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.recordsAddress
      },
      vuetify
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeDefined()

    Vue.nextTick(() => {
      done()
    })
  })
})
