<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { isAllowedEmailDomain, getEmailDomainError } from '../utils/emailDomain'
import { toast } from 'vue-sonner'

const router = useRouter()

const form = reactive({
  email: '',
  password: '',
  confirmPassword: ''
})

const loading = ref(false)

async function onSubmit() {
  if (!form.email || !form.password || !form.confirmPassword) {
    toast.error('Заполните все поля')
    return
  }

  if (!isAllowedEmailDomain(form.email)) {
    toast.error(getEmailDomainError())
    return
  }

  if (form.password.length < 6) {
    toast.error('Пароль должен содержать не менее 6 символов')
    return
  }

  if (form.password !== form.confirmPassword) {
    toast.error('Пароли не совпадают')
    return
  }

  loading.value = true

  try {
    await api.post('/auth/register', {
      email: form.email.trim(),
      password: form.password
    })

    toast.success('Регистрация выполнена')
    router.push('/login')
  } catch (e) {
    const message =
      e?.response?.data?.detail ||
      e?.message ||
      'Не удалось выполнить регистрацию'

    toast.error(message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">Регистрация</h1>

      <form class="auth-form" @submit.prevent="onSubmit">
        <div class="field">
          <label class="label">Почта</label>
          <input
            v-model="form.email"
            class="input"
            type="email"
            autocomplete="email"
            placeholder="Введите почту"
          />
        </div>

        <div class="field">
          <label class="label">Пароль</label>
          <input
            v-model="form.password"
            class="input"
            type="password"
            autocomplete="new-password"
            placeholder="Введите пароль"
          />
        </div>

        <div class="field">
          <label class="label">Повторите пароль</label>
          <input
            v-model="form.confirmPassword"
            class="input"
            type="password"
            autocomplete="new-password"
            placeholder="Повторите пароль"
          />
        </div>

        <button class="btn" type="submit" :disabled="loading">
          {{ loading ? 'Регистрируем…' : 'Зарегистрироваться' }}
        </button>
      </form>

      <div class="auth-footer">
        Уже есть аккаунт?
        <router-link to="/login">Войти</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 120px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border: 1px solid #e6edf5;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(16, 24, 40, 0.06);
  padding: 24px;
}

.auth-title {
  margin: 0 0 20px;
  font-size: 28px;
  font-weight: 700;
}

.auth-form {
  display: grid;
  gap: 16px;
}

.field {
  display: grid;
  gap: 8px;
}

.label {
  font-size: 14px;
  color: #334155;
}

.input {
  width: 100%;
  border: 1px solid #d7deea;
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 15px;
  outline: none;
  box-sizing: border-box;
}

.input:focus {
  border-color: #94a3b8;
}

.btn {
  margin-top: 6px;
  border: none;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 15px;
  cursor: pointer;
  background: #111827;
  color: #fff;
}

.btn:disabled {
  opacity: 0.65;
  cursor: default;
}

.auth-footer {
  margin-top: 16px;
  font-size: 14px;
  color: #475569;
}
</style>
