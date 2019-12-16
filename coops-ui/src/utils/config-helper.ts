import axios from '@/axios-auth'

export default {
  /**
   * fetch config from environment and API
   */
  fetchConfig () {
    const origin = window.location.origin
    const vueAppPath = process.env.VUE_APP_PATH
    const vueAppAuthPath = process.env.VUE_APP_AUTH_PATH

    if (!vueAppPath || !vueAppAuthPath) {
      throw new Error('failed to get env variables')
    }

    const baseUrl = `${origin}/${vueAppPath}/`
    sessionStorage.setItem('BASE_URL', baseUrl)
    console.log('Set Base URL to: ' + baseUrl)

    const authUrl = `${origin}/${vueAppAuthPath}/`
    sessionStorage.setItem('AUTH_URL', authUrl)
    console.log('Set Auth URL to: ' + authUrl)

    const url = `/${vueAppPath}/config/configuration.json`
    const headers = {
      'Accept': 'application/json',
      'ResponseType': 'application/json',
      'Cache-Control': 'no-cache'
    }

    return axios
      .get(url, { headers })
      .then(response => {
        const apiUrl = response.data['API_URL']
        axios.defaults.baseURL = apiUrl
        console.info('Set Legal API URL to: ' + apiUrl)

        const authApiUrl = response.data['AUTH_API_URL']
        sessionStorage.setItem('AUTH_API_URL', authApiUrl)
        console.info('Set Auth API URL to: ' + authApiUrl)

        const payApiUrl = response.data['PAY_API_URL']
        sessionStorage.setItem('PAY_API_URL', payApiUrl)
        console.info('Set Pay API URL to: ' + payApiUrl)

        const keycloakConfigUrl = response.data['KEYCLOAK_CONFIG_URL']
        sessionStorage.setItem('KEYCLOAK_CONFIG_URL', keycloakConfigUrl)
        console.info('Set KeyCloak config URL to: ' + keycloakConfigUrl)

        const addressCompleteKey = response.data['ADDRESS_COMPLETE_KEY']
        window['addressCompleteKey'] = addressCompleteKey
        console.info('Set Address Complete Key.')

        const ldClientId = response.data['LD_CLIENT_ID']
        window['ldClientId'] = ldClientId
        console.info('Set LD Client Id.')
      })
  }
}
