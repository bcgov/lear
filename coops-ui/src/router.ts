import Vue from 'vue'
import VueRouter from 'vue-router'
import routes from '@/routes'

Vue.use(VueRouter)

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes,
  scrollBehavior (to, from, savedPosition) {
    // see https://router.vuejs.org/guide/advanced/scroll-behavior.html
    return { x: 0, y: 0 }
  }
})

// if there is no saved Keycloak token, redirect to Auth URL
router.afterEach((to, from) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    const redirected = sessionStorage.getItem('REDIRECTED')
    console.log(`redirect check = '${redirected}'`)

    if (redirected !== 'true') {
      if (sessionStorage.getItem('KEYCLOAK_TOKEN')) {
        console.log('AUTH PASSED')
      } else {
        console.log('AUTH FAILED')
        sessionStorage.setItem('REDIRECTED', 'true')
        window.location.href = sessionStorage.getItem('AUTH_URL')
      }
    }
  }
})

export default router
