import axios from '@/axios-auth'

export default {
  /**
   * fetch config from API
   */
  fetchConfig () {
    const url = '/config/configuration.json'
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
        console.log('Set Base URL to: ' + apiUrl)

        const authUrl = response.data['AUTH_URL']
        sessionStorage.setItem('AUTH_URL', authUrl)
        console.log('Set Auth URL to: ' + authUrl)

        const authApiUrl = response.data['AUTH_API_URL']
        sessionStorage.setItem('AUTH_API_URL', authApiUrl)
        console.log('Set Auth API URL to: ' + authApiUrl)

        const payApiUrl = response.data['PAY_API_URL']
        sessionStorage.setItem('PAY_API_URL', payApiUrl)
        console.log('Set Pay API URL to: ' + payApiUrl)

        const addressCompleteKey = response.data['ADDRESS_COMPLETE_KEY']
        window['addressCompleteKey'] = addressCompleteKey
        console.log('Set Address Complete Key')
      })
  }
}
