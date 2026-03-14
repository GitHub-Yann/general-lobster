import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import FileManager from '../views/FileManager.vue'

const routes = [
  {
    path: '/',
    redirect: '/files'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/files',
    name: 'FileManager',
    component: FileManager,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/files')
  } else {
    next()
  }
})

export default router
