import Vue from 'vue'
import Vuetify from 'vuetify'

import EntityInfo from '@/components/EntityInfo.vue'
import Home from '@/views/Home.vue'
import axios from '@/axios-auth'
import sinon from 'sinon'
import store from '@/store'

Vue.use(Vuetify)

describe('EntityInfo.vue', () => {
  sessionStorage.setItem('KEYCLOAK_TOKEN', '1234abcd')
  sessionStorage.setItem('USERNAME', 'CP0001191')

  const ParentConstructor = Vue.extend(Home)
  let parentInstance = new ParentConstructor({ store: store })
  let parentvm = parentInstance.$mount()

  const Constructor = Vue.extend(EntityInfo)
  let instance = new Constructor({ store: store })
  let vm = instance.$mount()

  sinon.getStub = sinon.stub(axios, 'get')
  // stub ar to prevent errors
  sinon.getStub.withArgs('https://mock-lear-tools.pathfinder.gov.bc.ca/rest/legal-api/0.64/api/v1/businesses/' +
    'CP0001191/filings/annual_report?year=2017')
    .returns(new Promise((resolve) => resolve({
      data:
        {
          filing: {
            header: {
              name: 'annual report',
              date: '2016-04-08'
            },
            business_info: {
              founding_date: '2001-08-05',
              identifier: 'CP0001191',
              legal_name: 'legal name - CP0001191'
            },
            annual_report: {
              annual_general_meeting_date: '2016-04-08',
              certified_by: 'full name',
              email: 'no_one@never.get'
            }
          }
        }
    })))

  sinon.getStub.withArgs('https://mock-lear-tools.pathfinder.gov.bc.ca/rest/legal-api/0.64/api/v1/businesses/CP0001187')
    .returns(new Promise((resolve) => resolve({
      data:
        {
          business_info: {
            founding_date: '2001-08-05',
            identifier: 'CP0001191',
            legal_name: 'legal name - CP0001191'
          }
        }
    })))

  beforeEach((done) => {
    setTimeout(() => {
      done()
    }, 100)
  })

  afterEach((done) => {
    setTimeout(() => {
      done()
    }, 100)
  })

  it('shows all elements', () => {
    // expect business name, business no, incorp no, and status to be on the screen
    expect(vm.$el.querySelector('.entity-name').textContent).toEqual('legal name - CP0001191')
    expect(vm.$el.querySelector('.entity-status').textContent).toContain('In Good Standing')
    expect(vm.$el.querySelector('.business-number').textContent).toEqual('123456789')
    expect(vm.$el.querySelector('.incorp-number').textContent).toEqual('CP0001191')
  })

  it('handles empty data', () => {
    vm.$store.state.entityName = null
    vm.$store.state.entityStatus = null
    vm.$store.state.entityBusinessNo = null
    vm.$store.state.entityIncNo = null
    setTimeout(() => {
      expect(vm.$el.querySelector('.entity-name').textContent).toEqual('')
      expect(vm.$el.querySelector('.entity-status').textContent).toContain('')
      expect(vm.$el.querySelector('.business-number').textContent).toEqual('Not Available')
      expect(vm.$el.querySelector('.incorp-number').textContent).toEqual('Not Available')
    }, 10)
  })
})
