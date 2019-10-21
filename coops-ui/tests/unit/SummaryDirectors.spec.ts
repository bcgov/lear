// Libraries
import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

// Components
import { SummaryDirectors } from '@/components/Common'

// Store
import store from '@/store/store'

// Enums
import { EntityTypes } from '@/enums'

Vue.use(Vuetify)
Vue.use(Vuelidate)

let vuetify = new Vuetify({})

// Boilerplate to prevent the complaint "[Vuetify] Unable to locate target [data-app]"
const app: HTMLDivElement = document.createElement('div')
app.setAttribute('data-app', 'true')
document.body.append(app)

describe.only('Directors as a COOP', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.entityIncNo = 'CP0001191'
    store.state.entityType = EntityTypes.Coop
    const directors = [
      {
        'id': 1,
        'actions': [],
        'officer': {
          'firstName': 'Peter',
          'middleInitial': null,
          'lastName': 'Griffin'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line one',
          'streetAddressAdditional': null,
          'addressCity': 'mailing_address city',
          'addressCountry': 'mailing_address country',
          'postalCode': 'H0H0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': null
        },
        'title': null
      },
      {
        'id': 2,
        'actions': [],
        'officer': {
          'firstName': 'Joe',
          'middleInitial': 'P',
          'lastName': 'Swanson'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line #1',
          'streetAddressAdditional': 'Kirkintiloch',
          'addressCity': 'Glasgow',
          'addressCountry': 'UK',
          'postalCode': 'H0H 0H0',
          'addressRegion': 'Scotland',
          'deliveryInstructions': 'go to the back'
        },
        'title': 'Treasurer'
      },
      {
        'id': 3,
        'actions': ['ceased'],
        'officer': {
          'firstName': 'Steve',
          'middleInitial': 'P',
          'lastName': 'BadApple'
        },
        'deliveryAddress': {
          'streetAddress': 'Somewhere-address',
          'streetAddressAdditional': 'Unit 407',
          'addressCity': 'Surrey',
          'addressCountry': 'CA',
          'postalCode': 'H0H 0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': 'Who Knows'
        },
        'title': 'BadApple'
      }
    ]
    const Constructor = Vue.extend(SummaryDirectors)
    const instance = new Constructor({ store: store, propsData: { directors }, vuetify })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('initializes the director meta data properly', () => {
    // Verify Directors Summary List
    expect(vm.directorSummary.length).toEqual(2)
    expect(vm.directorSummary[0].id).toEqual(1)
    expect(vm.directorSummary[1].id).toEqual(2)

    // Verify Directors Summary List
    expect(vm.directorsCeased[0].id).toEqual(3)
  })

  it('initializes the director name data properly', () => {
    // Verify Directors Summary List
    expect(vm.directorSummary.length).toEqual(2)
    expect(vm.directorSummary[0].officer.firstName).toEqual('Peter')
    expect(vm.directorSummary[0].officer.middleInitial).toBeNull()
    expect(vm.directorSummary[0].officer.lastName).toEqual('Griffin')
    expect(vm.directorSummary[0].title).toBeNull()
    expect(vm.directorSummary[1].officer.firstName).toEqual('Joe')
    expect(vm.directorSummary[1].officer.middleInitial).toEqual('P')
    expect(vm.directorSummary[1].officer.lastName).toEqual('Swanson')
    expect(vm.directorSummary[1].title).toEqual('Treasurer')

    // Verify Directors Summary List
    expect(vm.directorsCeased[0].title).toEqual('BadApple')
    expect(vm.directorsCeased[0].officer.firstName).toEqual('Steve')
    expect(vm.directorsCeased[0].officer.middleInitial).toEqual('P')
    expect(vm.directorsCeased[0].officer.lastName).toEqual('BadApple')
  })

  it('initializes the director address data properly', () => {
    // check complete first address from Summary List
    expect(vm.directorSummary.length).toEqual(2)
    expect(vm.directorSummary[0].deliveryAddress.streetAddress).toEqual('mailing_address - address line one')
    expect(vm.directorSummary[0].deliveryAddress.addressCity).toEqual('mailing_address city')
    expect(vm.directorSummary[0].deliveryAddress.addressRegion).toEqual('BC')
    expect(vm.directorSummary[0].deliveryAddress.addressCountry).toEqual('mailing_address country')
    expect(vm.directorSummary[0].deliveryAddress.postalCode).toEqual('H0H0H0')
    expect(vm.directorSummary[0].deliveryAddress.deliveryInstructions).toEqual(null)

    // spot-check second address
    expect(vm.directorSummary[1].deliveryAddress.streetAddressAdditional).toEqual('Kirkintiloch')
    expect(vm.directorSummary[1].deliveryAddress.deliveryInstructions).toEqual('go to the back')
  })

  it('displays the list of directors', () => {
    const directorListUI = vm.$el.querySelectorAll('.director-list .container')

    // shows list of all directors in the UI, in reverse order in which they are in the json
    expect(directorListUI.length).toEqual(3)
    expect(directorListUI[2].textContent).toContain('Steve')
    expect(directorListUI[2].textContent).toContain('Somewhere-address')
    expect(directorListUI[1].textContent).toContain('Griffin')
    expect(directorListUI[1].textContent).toContain('mailing_address city')
    expect(directorListUI[0].textContent).toContain('Joe')
    expect(directorListUI[0].textContent).toContain('Glasgow')
  })
})

describe.only('Directors as a BCORP', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.entityIncNo = 'BC0001191'
    store.state.entityType = EntityTypes.BCorp
    const directors = [
      {
        'id': 1,
        'actions': [],
        'officer': {
          'firstName': 'Peter',
          'middleInitial': null,
          'lastName': 'Griffin'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line one',
          'streetAddressAdditional': null,
          'addressCity': 'mailing_address city',
          'addressCountry': 'mailing_address country',
          'postalCode': 'H0H0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': null
        },
        'mailingAddress': {
          'streetAddress': 'mailing_address - address line one',
          'streetAddressAdditional': null,
          'addressCity': 'mailing_address city',
          'addressCountry': 'mailing_address country',
          'postalCode': 'H0H0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': null
        },
        'title': null
      },
      {
        'id': 2,
        'actions': [],
        'officer': {
          'firstName': 'Joe',
          'middleInitial': 'P',
          'lastName': 'Swanson'
        },
        'deliveryAddress': {
          'streetAddress': 'mailing_address - address line #1',
          'streetAddressAdditional': 'Kirkintiloch',
          'addressCity': 'Glasgow',
          'addressCountry': 'UK',
          'postalCode': 'H0H 0H0',
          'addressRegion': 'Scotland',
          'deliveryInstructions': 'go to the back'
        },
        'mailingAddress': {
          'streetAddress': '1234 Clover St',
          'streetAddressAdditional': null,
          'addressCity': 'mockCity',
          'addressCountry': 'mockCountry',
          'postalCode': 'v1v2b2',
          'addressRegion': 'BC',
          'deliveryInstructions': null
        },
        'title': 'Treasurer'
      },
      {
        'id': 3,
        'actions': ['ceased'],
        'officer': {
          'firstName': 'Steve',
          'middleInitial': 'P',
          'lastName': 'BadApple'
        },
        'deliveryAddress': {
          'streetAddress': 'Somewhere-address',
          'streetAddressAdditional': 'Unit 407',
          'addressCity': 'Surrey',
          'addressCountry': 'CA',
          'postalCode': 'H0H 0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': 'Who Knows'
        },
        'mailingAddress': {
          'streetAddress': 'Somewhere-address',
          'streetAddressAdditional': 'Unit 407',
          'addressCity': 'Surrey',
          'addressCountry': 'CA',
          'postalCode': 'H0H 0H0',
          'addressRegion': 'BC',
          'deliveryInstructions': 'Who Knows'
        },
        'title': 'BadApple'
      }
    ]
    const Constructor = Vue.extend(SummaryDirectors)
    const instance = new Constructor({ store: store, propsData: { directors }, vuetify })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('initializes the director meta data properly', () => {
    // Verify Directors Summary List
    expect(vm.directorSummary.length).toEqual(2)
    expect(vm.directorSummary[0].id).toEqual(1)
    expect(vm.directorSummary[1].id).toEqual(2)

    // Verify Directors Summary List
    expect(vm.directorsCeased[0].id).toEqual(3)
  })

  it('initializes the director name data properly', () => {
    // Verify Directors Summary List
    expect(vm.directorSummary.length).toEqual(2)
    expect(vm.directorSummary[0].officer.firstName).toEqual('Peter')
    expect(vm.directorSummary[0].officer.middleInitial).toBeNull()
    expect(vm.directorSummary[0].officer.lastName).toEqual('Griffin')
    expect(vm.directorSummary[0].title).toBeNull()
    expect(vm.directorSummary[1].officer.firstName).toEqual('Joe')
    expect(vm.directorSummary[1].officer.middleInitial).toEqual('P')
    expect(vm.directorSummary[1].officer.lastName).toEqual('Swanson')
    expect(vm.directorSummary[1].title).toEqual('Treasurer')

    // Verify Directors Summary List
    expect(vm.directorsCeased[0].title).toEqual('BadApple')
    expect(vm.directorsCeased[0].officer.firstName).toEqual('Steve')
    expect(vm.directorsCeased[0].officer.middleInitial).toEqual('P')
    expect(vm.directorsCeased[0].officer.lastName).toEqual('BadApple')
  })

  it('initializes the director address data properly', () => {
    // check complete first address from Summary List
    expect(vm.directorSummary.length).toEqual(2)
    expect(vm.directorSummary[0].deliveryAddress.streetAddress).toEqual('mailing_address - address line one')
    expect(vm.directorSummary[0].deliveryAddress.addressCity).toEqual('mailing_address city')
    expect(vm.directorSummary[0].deliveryAddress.addressRegion).toEqual('BC')
    expect(vm.directorSummary[0].deliveryAddress.addressCountry).toEqual('mailing_address country')
    expect(vm.directorSummary[0].deliveryAddress.postalCode).toEqual('H0H0H0')
    expect(vm.directorSummary[0].deliveryAddress.deliveryInstructions).toEqual(null)

    // spot-check second address
    expect(vm.directorSummary[1].deliveryAddress.streetAddressAdditional).toEqual('Kirkintiloch')
    expect(vm.directorSummary[1].deliveryAddress.deliveryInstructions).toEqual('go to the back')

    // Spot-check mailing address
    expect(vm.directorSummary[0].mailingAddress.streetAddress).toEqual('mailing_address - address line one')
    expect(vm.directorSummary[1].mailingAddress.streetAddress).toEqual('1234 Clover St')
    expect(vm.directorsCeased[0].mailingAddress.streetAddress).toEqual('Somewhere-address')

  })

  it('displays the list of directors', () => {
    const directorListUI = vm.$el.querySelectorAll('.director-list .container')

    // shows list of all directors in the UI, in reverse order in which they are in the json
    expect(directorListUI.length).toEqual(3)
    expect(directorListUI[2].textContent).toContain('Steve')
    expect(directorListUI[2].textContent).toContain('Somewhere-address')
    expect(directorListUI[1].textContent).toContain('Griffin')
    expect(directorListUI[1].textContent).toContain('mailing_address city')
    expect(directorListUI[0].textContent).toContain('Joe')
    expect(directorListUI[0].textContent).toContain('Glasgow')

    // Check output when mailing and delivery address match
    expect(directorListUI[1].querySelector('.same-address').textContent).toContain('Same as Delivery')

  })
})
