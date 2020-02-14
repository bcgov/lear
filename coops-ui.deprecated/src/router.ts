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

// NAVIGATION GUARD NOT NEEDED AT THIS TIME
// router.afterEach((to, from) => {
//   const token = sessionStorage.getItem('KEYCLOAK_TOKEN')
//   // if we need authentication then redirect to Auth URL
//   if (to.matched.some(record => record.meta.requiresAuth) && !token) {
//     const authUrl = sessionStorage.getItem('AUTH_URL')
//     // assume Auth URL is always reachable
//     window.location.assign(authUrl)
//   }
// })

export default router
