import Dashboard from '@/views/Dashboard.vue'
import AnnualReport from '@/views/AnnualReport.vue'
import StandaloneDirectorsFiling from '@/views/StandaloneDirectorsFiling.vue'
import StandaloneOfficeAddressFiling from '@/views/StandaloneOfficeAddressFiling.vue'

export default [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: Dashboard,
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/annual-report',
    name: 'annual-report',
    component: AnnualReport,
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/standalone-directors',
    name: 'standalone-directors',
    component: StandaloneDirectorsFiling,
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/standalone-addresses',
    name: 'standalone-addresses',
    component: StandaloneOfficeAddressFiling,
    meta: {
      requiresAuth: true
    }
  },
  // {
  //   path: '/about',
  //   name: 'about',
  //   // route level code-splitting
  //   // this generates a separate chunk (about.[hash].js) for this route
  //   // which is lazy-loaded when the route is visited.
  //   // ref: https://cli.vuejs.org/guide/html-and-static-assets.html#prefetch
  //   component: () => import(/* webpackChunkName: "about" */ './views/About.vue')
  // },
  {
    // default/fallback route
    path: '*',
    redirect: '/'
  }
]
