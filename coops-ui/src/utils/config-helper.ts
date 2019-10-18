import axios from '@/axios-auth'

export default {
  /**
   * fetch config from API
   */
  fetchConfig () {
    const url = `/${process.env.VUE_APP_PATH}/config/configuration.json`
    const headers = {
      'Accept': 'application/json',
      'ResponseType': 'application/json',
      'Cache-Control': 'no-cache'
    }

    const baseUrl = `${window.location.origin}/${process.env.VUE_APP_PATH}/`
    sessionStorage.setItem('BASE_URL', baseUrl)
    console.log('Set Base URL to: ' + baseUrl)

    const authUrl = `${window.location.origin}/${process.env.VUE_APP_AUTH_PATH}/`
    sessionStorage.setItem('AUTH_URL', authUrl)
    console.log('Set Auth URL to: ' + authUrl)

    return axios
      .get(url, { headers })
      .then(response => {
        const apiUrl = response.data['API_URL']
        axios.defaults.baseURL = apiUrl
        console.log('Set Legal API URL to: ' + apiUrl)

        const authApiUrl = response.data['AUTH_API_URL']
        sessionStorage.setItem('AUTH_API_URL', authApiUrl)
        console.log('Set Auth API URL to: ' + authApiUrl)

        const payApiUrl = response.data['PAY_API_URL']
        sessionStorage.setItem('PAY_API_URL', payApiUrl)
        console.log('Set Pay API URL to: ' + payApiUrl)

        const addressCompleteKey = response.data['ADDRESS_COMPLETE_KEY']
        window['addressCompleteKey'] = addressCompleteKey
        console.log('Set Address Complete Key.')
      })
  }
}
