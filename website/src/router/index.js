import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import QuickStartView from '../views/QuickStartView.vue'
import AdvancedView from '../views/AdvancedView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/start',
    name: 'start',
    component: QuickStartView
  },
  {
    path: '/advanced',
    name: 'advanced',
    component: AdvancedView
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
