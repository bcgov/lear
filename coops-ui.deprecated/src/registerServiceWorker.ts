/* eslint-disable no-console */

import { register } from 'register-service-worker'

const confirmWindowText = 'A new version of the BC Registries application is available. \n\n' +
                          'Select OK to update now, or Cancel to update later. \n\n' +
                          'Note: Selecting OK will cause unsaved changes to be lost. ' +
                          'Select Cancel to save your changes and continue using the ' +
                          'current version of the application. \n\n' +
                          'The application will automatically update when you close your browser.'

if (process.env.NODE_ENV === 'production') {
  register(`${process.env.BASE_URL}service-worker.js`, {
    ready () {
      console.log(
        'App is being served from cache by a service worker.\n' +
        'For more details, visit https://goo.gl/AFskqB'
      )
    },
    registered () {
      console.log('Service worker has been registered.')
    },
    cached () {
      console.log('Content has been cached for offline use.')
    },
    updatefound () {
      console.log('New content is downloading.')
    },
    updated (registration) {
      console.log('New content is available; please refresh.')
      let confirmationResult = confirm(confirmWindowText)
      if (confirmationResult) { registration.waiting.postMessage({ action: 'skipWaiting' }) }
    },
    offline () {
      console.log('No internet connection found. App is running in offline mode.')
    },
    error (error) {
      console.error('Error during service worker registration:', error)
    }
  })

  let refreshing
  // safety check for IE11
  if (navigator && navigator.serviceWorker) {
    navigator.serviceWorker.addEventListener('controllerchange', e => {
      if (refreshing) return
      window.location.reload()
      refreshing = true
    })
  }
}
