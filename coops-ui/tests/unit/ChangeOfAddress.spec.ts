import Vue from 'vue'
import Vuetify from 'vuetify'
import Vuelidate from 'vuelidate'
import sinon from 'sinon'

import axios from '@/axios-auth'
import store from '@/store/store'
import RegisteredOfficeAddress from '@/components/AnnualReport/RegisteredOfficeAddress.vue'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('RegisteredOfficeAddress.vue', () => {
  let vm

  function click (id) {
    const button = vm.$el.querySelector(id)
    const window = button.ownerDocument.defaultView
    const click = new window.Event('click')
    button.dispatchEvent(click)
  }

  beforeEach(done => {
    // init store
    store.state.corpNum = 'CP0001191'

    // GET addresses
    sinon.stub(axios, 'get').withArgs('CP0001191/addresses')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            'mailingAddress': {
              'addressCity': 'Test City',
              'addressCountry': 'TA',
              'addressRegion': 'BC',
              'addressType': 'mailing',
              'deliveryInstructions': null,
              'postalCode': 'T3S3T3',
              'streetAddress': 'CP0001191-mailingAddress-Test Street',
              'streetAddressAdditional': null
            },
            'deliveryAddress': {
              'addressCity': 'Test City',
              'addressCountry': 'TA',
              'addressRegion': 'BC',
              'addressType': 'mailing',
              'deliveryInstructions': null,
              'postalCode': 'T3S3T3',
              'streetAddress': 'CP0001191-deliveryAddress-Test Street',
              'streetAddressAdditional': null
            }
          }
      })))

    const ChildConstructor = Vue.extend(RegisteredOfficeAddress)
    let childInstance = new ChildConstructor({ store: store })
    vm = childInstance.$mount()

    Vue.nextTick(() => {
      done()
    })
  })

  afterEach(() => {
    sinon.restore()
  })

  it('loads the addresses properly', () => {
    expect(vm.$data.MailingAddressStreet).toEqual('CP0001191-mailingAddress-Test Street')
    expect(vm.$data.MailingAddressStreetAdditional).toBeNull()
    expect(vm.$data.MailingAddressCity).toEqual('Test City')
    expect(vm.$data.MailingAddressRegion).toEqual('BC')
    expect(vm.$data.MailingAddressPostalCode).toEqual('T3S3T3')
    expect(vm.$data.MailingAddressCountry).toEqual('TA')
    expect(vm.$data.MailingAddressInstructions).toBeNull()

    expect(vm.$data.DeliveryAddressStreet).toEqual('CP0001191-deliveryAddress-Test Street')
    expect(vm.$data.DeliveryAddressStreetAdditional).toBeNull()
    expect(vm.$data.DeliveryAddressCity).toEqual('Test City')
    expect(vm.$data.DeliveryAddressRegion).toEqual('BC')
    expect(vm.$data.DeliveryAddressPostalCode).toEqual('T3S3T3')
    expect(vm.$data.DeliveryAddressCountry).toEqual('TA')
    expect(vm.$data.DeliveryAddressInstructions).toBeNull()

    console.log('Passed Test 1')
  })

  it('disables Change button when AGM Date is invalid', done => {
    // invalidate AGM Date
    vm.$store.state.agmDateValid = false

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#reg-off-addr-change-btn').disabled).toBe(true)

      console.log('Passed Test 2')
      done()
    })
  })

  it('enables Change button when AGM Date is valid', done => {
    // validate AGM Date
    vm.$store.state.agmDateValid = true

    Vue.nextTick(() => {
      expect(vm.$el.querySelector('#reg-off-addr-change-btn').disabled).toBe(false)

      console.log('Passed Test 3')
      done()
    })
  })

  it('displays the non-editable version of the registered office address', () => {
    expect(vm.$data.showAddressForm).toBe(false)
    if (vm.$el.querySelector('#delivery-address-display').style.length > 0) {
      expect(vm.$el.querySelector('#delivery-address-display').getAttribute('style'))
        .not.toContain('display: none;')
    }
    if (vm.$el.querySelector('#mailing-address-display').style.length > 0) {
      expect(vm.$el.querySelector('#mailing-address-display').getAttribute('style'))
        .not.toContain('display: none;')
    }
    expect(vm.$el.querySelector('#delivery-address-form').getAttribute('style'))
      .toContain('display: none;')
    expect(vm.$el.querySelector('#mailing-address-form').getAttribute('style'))
      .toContain('display: none;')

    console.log('Passed Test 4')
  })

  it('allows you to edit the addresses', done => {
    vm.$store.state.agmDateValid = true

    vm.$data.MailingAddressStreet = vm.$store.state.MailingAddressStreet
    vm.$data.MailingAddressStreetAdditional = vm.$store.state.MailingAddressStreetAdditional
    vm.$data.MailingAddressCity = vm.$store.state.MailingAddressCity
    vm.$data.MailingAddressRegion = vm.$store.state.MailingAddressRegion
    vm.$data.MailingAddressPostalCode = vm.$store.state.MailingAddressPostalCode
    vm.$data.MailingAddressCountry = vm.$store.state.MailingAddressCountry
    vm.$data.MailingAddressInstructions = vm.$store.state.MailingAddressInstructions

    vm.$data.DeliveryAddressStreet = vm.$store.state.DeliveryAddressStreet
    vm.$data.DeliveryAddressStreetAdditional = vm.$store.state.DeliveryAddressStreetAdditional
    vm.$data.DeliveryAddressCity = vm.$store.state.DeliveryAddressCity
    vm.$data.DeliveryAddressRegion = vm.$store.state.DeliveryAddressRegion
    vm.$data.DeliveryAddressPostalCode = vm.$store.state.DeliveryAddressPostalCode
    vm.$data.DeliveryAddressCountry = vm.$store.state.DeliveryAddressCountry
    vm.$data.DeliveryAddressInstructions = vm.$store.state.DeliveryAddressInstructions

    Vue.nextTick(() => {
      expect(vm.$store.state.regOffAddrChange).toBe(false)
      expect(vm.$data.showAddressForm).toBe(false)
      expect(vm.$el.querySelector('#reg-off-addr-change-btn')).not.toBeNull()
      expect(vm.$el.querySelector('#reg-off-addr-reset-btn')).toBeNull()

      click('#reg-off-addr-change-btn')
      Vue.nextTick(() => {
        // editable address form shown
        expect(vm.$data.showAddressForm).toBe(true)
        if (vm.$el.querySelector('#delivery-address-form').style.length > 0) {
          expect(vm.$el.querySelector('#delivery-address-form').getAttribute('style'))
            .not.toContain('display: none;')
        }
        if (vm.$el.querySelector('#mailing-address-form').style.length > 0) {
          expect(vm.$el.querySelector('#mailing-address-form').getAttribute('style'))
            .not.toContain('display: none;')
        }
        expect(vm.$el.querySelector('#delivery-address-display').getAttribute('style'))
          .toContain('height: 0px;')
        expect(vm.$el.querySelector('#mailing-address-display').getAttribute('style'))
          .toContain('height: 0px;')
        expect(vm.$data.inheritDeliveryAddress).toBe(true)
        expect(vm.$el.querySelector('#mailing-address-expanded').getAttribute('style'))
          .toContain('display: none;')

        vm.$data.inheritDeliveryAddress = false
        Vue.nextTick(() => {
          if (vm.$el.querySelector('#mailing-address-expanded').style.length > 0) {
            expect(vm.$el.querySelector('#mailing-address-expanded').getAttribute('style'))
              .not.toContain('display: none;')
          }
          expect(vm.$el.querySelector('#reg-off-update-addr-btn').disabled).toBe(true)
          expect(vm.$el.querySelector('#reg-off-cancel-addr-btn').disabled).toBe(false)

          vm.$data.DeliveryAddressStreet = null
          Vue.nextTick(() => {
            expect(vm.$el.querySelector('#reg-off-update-addr-btn').disabled).toBe(true)

            vm.$data.DeliveryAddressStreet = '1234'
            click('#reg-off-update-addr-btn')
            Vue.nextTick(() => {
              expect(vm.$data.showAddressForm).toBe(false)
              if (vm.$el.querySelector('#delivery-address-display').style.length > 0) {
                expect(vm.$el.querySelector('#delivery-address-display')
                  .getAttribute('style')).not.toContain('display: none;')
              }
              if (vm.$el.querySelector('#mailing-address-display').style.length > 0) {
                expect(vm.$el.querySelector('#mailing-address-display')
                  .getAttribute('style')).not.toContain('display: none;')
              }
              expect(vm.$el.querySelector('#delivery-address-form').getAttribute('style'))
                .toContain('height: 0px;')
              expect(vm.$el.querySelector('#mailing-address-form').getAttribute('style'))
                .toContain('height: 0px;')
              expect(vm.$store.state.regOffAddrChange).toBe(true)
              expect(vm.$data.DeliveryAddressStreet).toEqual('1234')
              expect(vm.$data.MailingAddressStreet).not.toBeDefined()
              expect(vm.$el.querySelector('#reg-off-addr-reset-btn')).not.toBeNull()

              click('#reg-off-addr-change-btn')
              Vue.nextTick(() => {
                vm.$data.DeliveryAddressStreet = '12345678'
                vm.$data.MailingAddressStreet = '12345678'
                expect(vm.$el.querySelector('#reg-off-cancel-addr-btn')).not.toBeNull()

                click('#reg-off-cancel-addr-btn')
                Vue.nextTick(() => {
                  expect(vm.$data.DeliveryAddressStreet).toEqual('CP0001191-deliveryAddress-Test Street')
                  expect(vm.$data.MailingAddressStreet).toEqual('CP0001191-mailingAddress-Test Street')
                  expect(vm.$el.querySelector('#reg-off-addr-reset-btn')).not.toBeNull()

                  click('#reg-off-addr-reset-btn')
                  Vue.nextTick(() => {
                    expect(vm.$data.DeliveryAddressStreet).toEqual('CP0001191-deliveryAddress-Test Street')
                    expect(vm.$store.state.regOffAddrChange).toBe(false)
                    expect(vm.$el.querySelector('#reg-off-addr-reset-btn')).toBeNull()

                    console.log('Passed Test 5')
                    done()
                  })
                })
              })
            })
          })
        })
      })
    })
  })
})
