import Keycloak, { KeycloakInitOptions, KeycloakInstance } from 'keycloak-js'

class TokenServices {
  private kc: KeycloakInstance
  private static instance: TokenServices
  private kcLoaded
  private counter = 0
  private REFRESH_ATTEMPT_INTERVAL = 10 // in seconds
  private timerId
  private kcOptions: KeycloakInitOptions = {
    onLoad: 'login-required',
    checkLoginIframe: false,
    timeSkew: 0,
    token: sessionStorage.getItem('KEYCLOAK_TOKEN'),
    refreshToken: sessionStorage.getItem('KEYCLOAK_REFRESH_TOKEN'),
    idToken: sessionStorage.getItem('KEYCLOAK_ID_TOKEN')
  }

  initUsingKc (kcInstance: KeycloakInstance) {
    console.info('[TokenServices] KC Instance registered using kc instance')
    this.kc = kcInstance
  }

  initUsingUrl (keyCloakConfigurl: string) {
    console.info('[TokenServices] KC Instance registered using kc URL')
    var self = this
    return new Promise((resolve, reject) => {
      this.kc = Keycloak(keyCloakConfigurl)
      this.kc.init(this.kcOptions
      ).success(function (authenticated) {
        console.info('[TokenServices] is User Authenticated:Syncing' + authenticated)
        self.syncSessionStorage()
        resolve(self.kc.token)
      }).error(function (err) {
        console.info('[TokenServices] Fatal Error:Could not Initialise KC instance' + err)
        reject(new Error('Could not Initialise KC'))
      })
    })
  }

  scheduleRefreshTimer (refreshEarlyTime: number = 0) {
    console.info('[TokenServices Starting the timer] ')
    let refreshEarlyTimeinMilliseconds = Math.max(this.REFRESH_ATTEMPT_INTERVAL, refreshEarlyTime) * 1000
    this.scheduleRefreshToken(refreshEarlyTimeinMilliseconds)
  }

  refreshToken () {
    console.log('[TokenServices] One time Token Refreshing ')
    return new Promise((resolve, reject) => {
      this.kc.updateToken(-1)
        .success(refreshed => {
          if (refreshed) {
            console.log('[TokenServices] One time Token Refreshed ')
            this.syncSessionStorage()
            resolve()
          }
        })
        .error(() => {
          // this.cleanupSession()
          reject(new Error('Could not refresh Token'))
        })
    })
  }

  stopRefreshTimer () {
    console.info('[TokenServices Stopping the timer] ')
    clearTimeout(this.timerId)
  }

  private scheduleRefreshToken (refreshEarlyTimeinMilliseconds: number) {
    let self = this

    // check if refresh token is still valid . Or else clear all timers and throw errors
    let refreshTokenExpiresIn =
      self.kc.refreshTokenParsed['exp'] - Math.ceil(new Date().getTime() / 1000) + self.kc.timeSkew
    if (refreshTokenExpiresIn < 0) {
      throw new Error('Refresh Token Expired..No more token refreshes')
    }

    let expiresIn = self.kc.tokenParsed['exp'] - Math.ceil(new Date().getTime() / 1000) + self.kc.timeSkew
    let refreshInMilliSeconds = (expiresIn * 1000) - refreshEarlyTimeinMilliseconds // in milliseconds
    console.info('[TokenServices] Token Expires in %s Seconds:', expiresIn)
    console.info('[TokenServices] Token Refreshal Scheduled in %s Seconds', (refreshInMilliSeconds / 1000))
    this.timerId = setTimeout(() => {
      console.log('[TokenServices] Refreshing Token Attempt: %s ', ++this.counter)
      this.kc.updateToken(-1)
        .success(refreshed => {
          if (refreshed) {
            console.log('successfully refreshed')
            this.syncSessionStorage()
            this.scheduleRefreshToken(refreshEarlyTimeinMilliseconds)
          }
        })
        .error(() => {
          clearTimeout(this.timerId)
          console.log('refresh failed')
        })
    }, refreshInMilliSeconds)
    console.log('[TokenServices] Timer id:' + this.timerId)
  }

  private syncSessionStorage () {
    sessionStorage.setItem('KEYCLOAK_TOKEN', this.kc.token)
    sessionStorage.setItem('KEYCLOAK_REFRESH_TOKEN', this.kc.refreshToken)
    sessionStorage.setItem('ID_TOKEN', this.kc.idToken)
  }

  decodeToken () {
    try {
      let token = sessionStorage.getItem('KEYCLOAK_TOKEN')
      const base64Url = token.split('.')[1]
      const base64 = decodeURIComponent(window.atob(base64Url).split('').map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      return JSON.parse(base64)
    } catch (error) {
      throw new Error('Error parsing JWT - ' + error)
    }
  }
}

export default TokenServices
