import Vue from 'vue'
import Vuelidate from 'vuelidate'
import Vuetify from 'vuetify'
import store from '@/store/store'

import { OfficeAddresses } from '@/components/common'
import { mount, Wrapper } from '@vue/test-utils'
import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe('OfficeAddresses as a COOP', () => {
  let vm

  beforeAll(() => {
    // init store
    store.state.entityType = EntityTypes.COOP
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
  })

  const draftAddresses = {
    registeredOffice: {
      deliveryAddress: {
        addressCity: 'delCityDraft',
        addressCountry: 'delCountryDraft',
        addressRegion: 'delRegionDraft',
        deliveryInstructions: 'delInstructionsDraft',
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
    }
  }

  it('loads the current office addresses properly', () => {
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        registeredAddress: store.state.registeredAddress
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify the `same as above text is not displayed
    expect(vm.$el.querySelector('#sameAsAbove')).toBeNull()

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
  })

  it('loads the current office addresses properly from a draft filing', () => {
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        addresses: draftAddresses
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify the `same as above text is not displayed
    expect(vm.$el.querySelector('#sameAsAbove')).toBeNull()

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
  })

  it('displays the same address as above text when the addresses match', () => {
    const registeredAddress = {
      deliveryAddress: {
        addressCity: 'sameCity',
        addressCountry: 'sameCountry',
        addressRegion: 'sameRegion',
        deliveryInstructions: 'sameInstructions',
        postalCode: 'samePostal',
        streetAddress: 'sameStreet',
        streetAddressAdditional: 'sameStreetAdd'
      },
      mailingAddress: {
        addressCity: 'sameCity',
        addressCountry: 'sameCountry',
        addressRegion: 'sameRegion',
        deliveryInstructions: 'sameInstructions',
        postalCode: 'samePostal',
        streetAddress: 'sameStreet',
        streetAddressAdditional: 'sameStreetAdd'
      }
    }
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        registeredAddress: registeredAddress
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify `same as above` text is displayed
    expect(vm.$el.querySelector('#sameAsAbove').textContent).toContain('Mailing Address same as above')

    const deliveryAddress = vm.deliveryAddress
    expect(deliveryAddress['streetAddress']).toEqual('sameStreet')
    expect(deliveryAddress['streetAddressAdditional']).toEqual('sameStreetAdd')
    expect(deliveryAddress['addressCity']).toEqual('sameCity')
    expect(deliveryAddress['addressRegion']).toEqual('sameRegion')
    expect(deliveryAddress['postalCode']).toEqual('samePostal')
    expect(deliveryAddress['addressCountry']).toEqual('sameCountry')
    expect(deliveryAddress['deliveryInstructions']).toEqual('sameInstructions')

    const mailingAddress = vm.registeredAddress.mailingAddress
    expect(mailingAddress).toEqual(deliveryAddress)
  })

  it('does not display the same address as above text when the addresses do not match', () => {
    const registeredAddress = {
      deliveryAddress: {
        addressCity: 'sameCity',
        addressCountry: 'sameCountry',
        addressRegion: 'sameRegion',
        deliveryInstructions: 'sameInstructions',
        postalCode: 'samePostal',
        streetAddress: 'sameStreet',
        streetAddressAdditional: 'sameStreetAdd'
      },
      mailingAddress: {
        addressCity: 'sameCity',
        addressCountry: 'sameCountry',
        addressRegion: 'sameRegion',
        deliveryInstructions: 'sameInstructions',
        postalCode: 'samePostal',
        streetAddress: 'notSameStreet',
        streetAddressAdditional: 'sameStreetAdd'
      }
    }
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        registeredAddress: registeredAddress
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify the `same as above text is not displayed
    expect(vm.$el.querySelector('#sameAsAbove')).toBeNull()

    const deliveryAddress = vm.deliveryAddress
    expect(deliveryAddress['streetAddress']).toEqual('sameStreet')
    expect(deliveryAddress['streetAddressAdditional']).toEqual('sameStreetAdd')
    expect(deliveryAddress['addressCity']).toEqual('sameCity')
    expect(deliveryAddress['addressRegion']).toEqual('sameRegion')
    expect(deliveryAddress['postalCode']).toEqual('samePostal')
    expect(deliveryAddress['addressCountry']).toEqual('sameCountry')
    expect(deliveryAddress['deliveryInstructions']).toEqual('sameInstructions')

    const mailingAddress = vm.registeredAddress.mailingAddress
    expect(mailingAddress).not.toEqual(deliveryAddress)
  })

  it('has enabled Change button', done => {
    const wrapper: Wrapper<OfficeAddresses> = mount(OfficeAddresses, {
      sync: false,
      propsData: {
        componentEnabled: true,
        registeredAddress: store.state.registeredAddress
      },
      store,
      vuetify
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeUndefined()

    done()
  })

  it('has disabled Change button', () => {
    const wrapper: Wrapper<OfficeAddresses> = mount(OfficeAddresses, {
      sync: false,
      propsData: {
        componentEnabled: false,
        registeredAddress: store.state.registeredAddress
      },
      store,
      vuetify
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeDefined()
  })
})

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

  const draftAddresses = {
    registeredOffice: {
      deliveryAddress: {
        addressCity: 'delCityDraft',
        addressCountry: 'delCountryDraft',
        addressRegion: 'delRegionDraft',
        deliveryInstructions: 'delInstructionsDraft',
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

  it('loads the current office addresses properly', async () => {
    const Constructor = Vue.extend(OfficeAddresses)
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
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = await new Constructor({
      propsData: {
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.registeredAddress
      },
      store,
      vuetify
    })
    vm = instance.$mount()

    // Verify the `same as above text is not displayed
    expect(vm.$el.querySelector('#sameAsAbove')).toBeNull()

    // Verify the `same as registered` text is displayed
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

  it('loads the current office addresses properly from a draft filing', () => {
    const Constructor = Vue.extend(OfficeAddresses)
    const instance = new Constructor({
      propsData: {
        addresses: draftAddresses,
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
  })

  it('has enabled Change button', () => {
    const wrapper: Wrapper<OfficeAddresses> = mount(OfficeAddresses, {
      sync: false,
      propsData: {
        componentEnabled: true,
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.recordsAddress
      },
      store,
      vuetify
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeUndefined()
  })

  it('has disabled Change button', () => {
    const wrapper: Wrapper<OfficeAddresses> = mount(OfficeAddresses, {
      sync: false,
      propsData: {
        componentEnabled: false,
        registeredAddress: store.state.registeredAddress,
        recordsAddress: store.state.recordsAddress
      },
      store,
      vuetify
    })

    expect(wrapper.find('#reg-off-addr-change-btn').attributes('disabled')).toBeDefined()
  })
})
