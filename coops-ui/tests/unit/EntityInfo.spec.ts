import Vue from 'vue'
import Vuetify from 'vuetify'

import EntityInfo from '@/components/EntityInfo.vue'
import App from '@/App.vue'
import AnnualReport from '@/views/AnnualReport.vue'
import axios from '@/axios-auth'
import sinon from 'sinon'
import store from '@/store'
import Vuelidate from 'vuelidate'

Vue.use(Vuetify)
Vue.use(Vuelidate)

describe('EntityInfo.vue', () => {
  // just need a token that can get parsed properly (will be expired but doesn't matter for tests)
  sessionStorage.setItem('KEYCLOAK_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJUbWdtZUk0MnVsdUZ0N' +
    '3FQbmUtcTEzdDUwa0JDbjF3bHF6dHN0UGdUM1dFIn0.eyJqdGkiOiIxYzQ2YjIzOS02ZWY0LTQxYTQtYThmMy05N2M5M2IyNmNlMjAiLCJle' +
    'HAiOjE1NTcxNzMyNTYsIm5iZiI6MCwiaWF0IjoxNTU3MTY5NjU2LCJpc3MiOiJodHRwczovL3Nzby1kZXYucGF0aGZpbmRlci5nb3YuYmMuY2' +
    'EvYXV0aC9yZWFsbXMvZmNmMGtwcXIiLCJhdWQiOiJzYmMtYXV0aC13ZWIiLCJzdWIiOiIwMzZlN2I4Ny0zZTQxLTQ2MTMtYjFiYy04NWU5OTA' +
    'xNTgzNzAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzYmMtYXV0aC13ZWIiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJkOGZmYjk4' +
    'OS0zNzRlLTRhYTktODc4OS03YTRkODA1ZjNkOTAiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly8xOTIuMTY4LjAuMTM6O' +
    'DA4MC8iLCIxOTIuMTY4LjAuMTMiLCIqIiwiaHR0cDovLzE5Mi4xNjguMC4xMzo4MDgwIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJlZGl' +
    '0IiwidW1hX2F1dGhvcml6YXRpb24iLCJiYXNpYyJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY' +
    '291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInByZWZlcnJlZF91c2VybmFtZSI6ImNwMDAwMTE5MSJ9.Ou' +
    'JLtzYCnkp5KXSiudGFJY6hTSvdE3KokhkEzqU-icxAzQwZSTYbzZQdGsIScy4-DIWHahIGp9L-e6mYlQSQta2rK2Kte85MxThubyw0096UOtAE' +
    'wnS9VURHXPUm4ZUyI4ECkyLlFywOPxAftNdeSYeJx26GHBCvo6uR9Zv6A3yTlJy3B1HJxBWk_6xTAzGPPDCLoyKGeIxGidGujKCKCAfXRMrjhX' +
    'yBv90XzDgZ-To-6_jMjSjBX6Dtq7icdZYLWWDdrhjCpJA5CKS0PlSgeH1Yq4rHd8Ztp5cvVdJFxt87gIopIOQvcy4ji0gtaovgUhiyg07gXGl8' +
    'dGZwn1tpLA')

  let rootvm
  let parentvm
  let vm

  sinon.getStub = sinon.stub(axios, 'get')

  beforeEach((done) => {
    // stub ar to prevent errors
    sinon.getStub.withArgs('CP0001191/filings/annual_report?year=2017')
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

    sinon.getStub.withArgs('CP0001187')
      .returns(new Promise((resolve) => resolve({
        data:
          {
            business_info: {
              founding_date: '2001-08-05',
              identifier: 'CP0001191',
              legal_name: 'test name - CP0001191'
            }
          }
      })))
    const RootConstructor = Vue.extend(App)
    let rootInstance = new RootConstructor({ store: store })
    rootvm = rootInstance.$mount()

    const ParentConstructor = Vue.extend(AnnualReport)
    let parentInstance = new ParentConstructor({ store: store })
    parentvm = parentInstance.$mount()

    const Constructor = Vue.extend(EntityInfo)
    let instance = new Constructor({ store: store })
    vm = instance.$mount()
    setTimeout(() => {
      done()
    }, 100)
  })

  afterEach((done) => {
    sinon.restore()
    setTimeout(() => {
      done()
    }, 100)
  })

  it('shows all elements', () => {
    // expect business name, business no, incorp no, and status to be on the screen
    expect(vm.$el.querySelector('.entity-name').textContent).toEqual('test name - CP0001191')
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
