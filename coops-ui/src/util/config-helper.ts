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
        console.log('Set axios.defaults.baseURL to: ' + apiUrl)

        const authUrl = response.data['AUTH_URL']
        sessionStorage.setItem('AUTH_URL', authUrl)
        console.log('Set uthUrl to: ' + authUrl)

        const authApiUrl = response.data['AUTH_API_URL']
        sessionStorage.setItem('AUTH_API_URL', authApiUrl)
        console.log('Set authApiUrl to: ' + authApiUrl)

        const payApiUrl = response.data['PAY_API_URL']
        sessionStorage.setItem('PAY_API_URL', payApiUrl)
        console.log('Set payApiUrl to: ' + payApiUrl)

        const addressCompleteKey = response.data['ADDRESS_COMPLETE_KEY']
        window['addressCompleteKey'] = addressCompleteKey
        console.log('Set addressCompleteKey')
      })
  }
}
