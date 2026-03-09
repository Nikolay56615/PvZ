<!-- src/App.vue -->
<template>
  <div class="container">
    <header class="header">
      <div class="brand">
        <div class="logo"></div>
        <h1 class="title">PVZ · Мониторинг влажности</h1>
      </div>

      <nav class="tabs">
        <router-link to="/" class="tab">
          Главная
        </router-link>

        <router-link to="/charts" class="tab">
          Графики
        </router-link>

        <router-link v-if="isAuth" to="/tenants" class="tab">
          Тенанты
        </router-link>

        <router-link v-if="isAuth" to="/map" class="tab">
          Карта
        </router-link>

        <button class="tab" type="button">Управление</button>
        <button class="tab" type="button">Настройки</button>

        <span style="flex:1"></span>

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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'

const router = useRouter()
const toast = useToast()

const isAuth = ref(false)
const userEmail = ref('')

onMounted(() => {
  const token = localStorage.getItem('pvz_token')
  const email = localStorage.getItem('pvz_email')

  isAuth.value = !!token
  userEmail.value = email || ''
})

function handleLogout() {
  localStorage.removeItem('pvz_token')
  localStorage.removeItem('pvz_email')

  isAuth.value = false
  userEmail.value = ''

  toast.info('Вы вышли из аккаунта')
  router.push('/login')
}
</script>

<style scoped>
.user-label {
  margin-right: 8px;
}
</style>