import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
    },
    {
      path: '/',
      name: 'Home',
      component: () => import('../views/Home.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/memory/:id',
      name: 'MemoryDetail',
      component: () => import('../views/MemoryDetail.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/memory/:id/showcase',
      name: 'Showcase',
      component: () => import('../views/Showcase.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/sync',
      name: 'Sync',
      component: () => import('../views/Sync.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/baidu-sync/:tripId',
      name: 'BaiduSync',
      component: () => import('../views/BaiduSync.vue'),
      meta: { requiresAuth: true },
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
