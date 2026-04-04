<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useToast } from 'vue-toastification'
import { isAllowedEmailDomain, getEmailDomainError } from '../utils/emailDomain'

const router = useRouter()
const toast = useToast()

const loginValue = ref('')
const password = ref('')
const loading = ref(false)

const validLogin = computed(() => /^[A-Za-z0-9._-]+(?:@[A-Za-z0-9.-]+\.[A-Za-z]{2,})?$/.test(loginValue.value.trim()))
const validPassword = computed(() => /^[A-Za-z0-9!@#$%^&*._-]+$/.test(password.value))

async function onSubmit() {
  if (!loginValue.value.trim() || !password.value) {
    toast.error('Введите email/логин и пароль')
    return
  }

  if (!validLogin.value) {
    toast.error('Некорректный email или логин. Допустимы латиница, цифры и . _ -')
    return
  }

  if (loginValue.value.includes('@') && !isAllowedEmailDomain(loginValue.value.trim())) {
    toast.error(getEmailDomainError())
    return
  }

  if (!validPassword.value) {
    toast.error('Пароль может содержать только латиницу, цифры и !@#$%^&*._-')
    return
  }

  loading.value = true
  try {
    const res = await api.post('/auth/login', {
      email: loginValue.value.trim(),
      password: password.value,
    })

    if (res?.access_token) {
      localStorage.setItem('pvz_token', res.access_token)
    } else if (res?.token) {
      localStorage.setItem('pvz_token', res.token)
    }

    if (res?.user) {
      localStorage.setItem('pvz_user', JSON.stringify(res.user))
    }

    toast.success(`Добро пожаловать, ${loginValue.value}!`)
    router.push('/')
  } catch (e) {
    toast.error(e?.message || 'Не удалось войти. Проверьте данные или попробуйте позже.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">Вход</h1>
      <p class="auth-subtitle">Войдите в систему для доступа к управлению устройствами</p>

      <form class="auth-form" @submit.prevent="onSubmit">
        <label class="auth-label">
          Email или логин
          <input
            v-model="loginValue"
            type="text"
            class="input"
            placeholder="Введите email или логин"
            autocomplete="username"
          />
        </label>

        <label class="auth-label">
          Пароль
          <input
            v-model="password"
            type="password"
            class="input"
            placeholder="Введите пароль"
            autocomplete="current-password"
          />
        </label>

        <button class="btn auth-btn" type="submit" :disabled="loading">
          {{ loading ? 'Входим...' : 'Войти' }}
        </button>
      </form>

      <p class="auth-footer">
        Нет аккаунта?
        <router-link to="/register">Зарегистрироваться</router-link>
      </p>
    </div>
  </section>
</template>
