import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import DirectorListSm from '@/components/Dashboard/DirectorListSm.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('DirectorListSm.vue', () => {
  let vm

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'

    // GET directors
    sinon.stub(axios, 'get').withArgs('CP0001191/directors')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            directors: [
              {
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
              }
            ]
          }
      })))

    const constructor = Vue.extend(DirectorListSm)
    const instance = new constructor({ store: store })
    vm = instance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('loads and displays the directors properly', () => {
    expect(vm.directors).not.toBeNull()
    expect(vm.directors.length).toEqual(2)
  })
})
