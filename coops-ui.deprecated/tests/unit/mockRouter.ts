/**
 * Helper function that will provide us with an instance of VueRouter
 * populated with the application routes.
 * ref: https://medium.com/@sarngru/vue-router-unit-testing-navigation-6cc0b0f86811
 */

import routes from '@/routes'
import VueRouter from 'vue-router'
import { mockRouterComponents } from 'vue-test-utils-helpers'

export default {
  mock () {
    // stub out the components that the routes point to
    // as we don't want to load and render real components
    const clearedRoutes = mockRouterComponents(routes)
    return new VueRouter({
      mode: 'abstract',
      routes: clearedRoutes
    })
  }
}
