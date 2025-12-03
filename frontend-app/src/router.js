// src/router.js
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './components/HomeView.vue'
import ChartsView from './components/ChartsView.vue'
import LoginView from './components/LoginView.vue'
import RegisterView from './components/RegisterView.vue'
import { useAuth } from './auth'

const routes = [
  { path: '/', component: HomeView },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  {
    path: '/charts',
    component: ChartsView,
    meta: { requiresAuth: true }
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const { isAuth } = useAuth()
  if (to.meta.requiresAuth && !isAuth.value) {
    next('/login')
  } else {
    next()
  }
})
