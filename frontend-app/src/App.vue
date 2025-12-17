<!-- src/App.vue -->
<template>
  <div class="container">
    <header class="header">
      <div class="brand">
        <div class="logo"></div>
        <h1 class="title">PVZ · Мониторинг влажности</h1>
      </div>

      <nav class="tabs">
        <router-link
          to="/"
          :class="['tab', { active: route.path === '/' }]"
        >
          Главная
        </router-link>

        <router-link
          to="/charts"
          :class="['tab', { active: route.path === '/charts' }]"
        >
          Графики
        </router-link>

        <!-- пока заглушки -->
        <button class="tab" type="button">Карта</button>
        <button class="tab" type="button">Управление</button>
        <button class="tab" type="button">Настройки</button>

        <span style="flex:1"></span>

        <!-- справа: либо "войти/регистрация", либо "вошли как / выйти" -->
        <template v-if="isAuth">
          <span class="helper user-label">
            Вошли как {{ userEmail }}
          </span>
          <button class="tab" type="button" @click="handleLogout">
            Выйти
          </button>
        </template>

        <template v-else>
          <router-link to="/login" class="tab">
            Войти
          </router-link>
          <router-link to="/register" class="tab">
            Регистрация
          </router-link>
        </template>
      </nav>
    </header>

    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { useAuth } from './auth'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { isAuth, userEmail, logout } = useAuth()

function handleLogout() {
  logout()
  toast.info('Вы вышли из аккаунта')
  router.push('/login')
}
</script>

<style scoped>
.user-label {
  margin-right: 8px;
}
</style>
