import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/Home.vue'
import AnnualReport from './views/AnnualReport.vue'
import AnnualReportAlt from './views/AnnualReportAlt.vue'
import Dashboard from './views/Dashboard.vue'
import DashboardSuccess from './views/DashboardSuccess.vue'
import Payment from './views/Payment.vue'
import PaymentCart from './views/PaymentCart.vue'
import PaymentInfo from './views/PaymentInfo.vue'

Vue.use(Router)

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/dashboardsuccess',
      name: 'dashboardSuccess',
      component: DashboardSuccess
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (about.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import(/* webpackChunkName: "about" */ './views/About.vue')
    },
    {
      path: '/AnnualReport',
      name: 'annual report prototype',
      component: AnnualReport
    },
    {
      path: '/AnnualReportAlt',
      name: 'annual report prototype alt',
      component: AnnualReportAlt
    },
    {
      path: '/Payment',
      name: 'PayBC',
      component: Payment,
      props: true
    },
    {
      path: '/PaymentCart',
      name: 'PayBC',
      component: PaymentCart,
      props: true
    },
    {
      path: '/PaymentInfo',
      name: 'PayBC',
      component: PaymentInfo,
      props: true
    }
  ]
})