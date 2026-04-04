<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useToast } from 'vue-toastification'
import { isAllowedEmailDomain, getEmailDomainError } from '../utils/emailDomain'

const router = useRouter()
const toast = useToast()

const email = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)

const validEmail = computed(() => /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email.value.trim()))
const validPassword = computed(() => /^[A-Za-z0-9!@#$%^&*._-]+$/.test(password.value))

async function onSubmit() {
  if (!email.value.trim() || !password.value || !password2.value) {
    toast.error('Заполни все поля')
    return
  }

  if (!validEmail.value) {
    toast.error('Некорректный email. Допустимы только латиница, цифры и ._%+-')
    return
  }

  if (!isAllowedEmailDomain(email.value.trim())) {
    toast.error(getEmailDomainError())
    return
  }

  if (!validPassword.value) {
    toast.error('Пароль может содержать только латиницу, цифры и !@#$%^&*._-')
    return
  }

  if (password.value !== password2.value) {
    toast.error('Пароли не совпадают')
    return
  }

  loading.value = true
  try {
    const res = await api.post('/auth/register', {
      email: email.value.trim(),
      password: password.value,
    })

    if (res?.access_token) {
      localStorage.setItem('pvz_token', res.access_token)
      if (res?.user) {
        localStorage.setItem('pvz_user', JSON.stringify(res.user))
      }
      toast.success('Аккаунт создан и вы вошли.')
      router.push('/')
      return
    }

    toast.success('Аккаунт создан. Теперь войдите.')
    router.push('/login')
  } catch (e) {
    toast.error(e?.body?.detail || e?.message || 'Не удалось создать аккаунт. Попробуйте позже.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">Регистрация</h1>
      <p class="auth-subtitle">Создай аккаунт для доступа к системе</p>

      <form class="auth-form" @submit.prevent="onSubmit">
        <label class="auth-label">
          Email
          <input
            v-model="email"
            type="email"
            class="input"
            placeholder="Введите email"
            autocomplete="email"
          />
        </label>

        <label class="auth-label">
          Пароль
          <input
            v-model="password"
            type="password"
            class="input"
            placeholder="Введите пароль"
            autocomplete="new-password"
          />
        </label>

        <label class="auth-label">
          Повторите пароль
          <input
            v-model="password2"
            type="password"
            class="input"
            placeholder="Повторите пароль"
            autocomplete="new-password"
          />
        </label>

        <button class="btn auth-btn" type="submit" :disabled="loading">
          {{ loading ? 'Создаем аккаунт...' : 'Зарегистрироваться' }}
        </button>
      </form>

      <p class="auth-footer">
        Уже есть аккаунт?
        <router-link to="/login">Войти</router-link>
      </p>
    </div>
  </section>
</template>
