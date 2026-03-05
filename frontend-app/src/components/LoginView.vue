<template>
  <div class="card p-28" style="max-width:420px; margin:40px auto">
    <h2 class="section-title" style="text-align:center">Вход</h2>

    <div class="form">
      <label class="label">Email или логин</label>
      <input
        class="input"
        v-model="loginValue"
        type="text"
        placeholder="you@example.com или admin"
      />

      <label class="label">Пароль</label>
      <input
        class="input"
        v-model="password"
        type="password"
        placeholder="••••••••"
      />

      <button class="btn primary mt-20" type="button" @click="loginUser">
        Войти
      </button>

      <div class="helper" style="margin-top:12px; text-align:center">
        Нет аккаунта?
        <router-link to="/register">Зарегистрироваться</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useToast } from 'vue-toastification'
import { useRouter } from 'vue-router'
import { useAuth } from '../auth'

const toast = useToast()
const router = useRouter()
const { login } = useAuth()

const loginValue = ref('')
const password = ref('')

// email или логин: либо валидный email, либо строка из латиницы/цифр/._-
const loginRe =
  /^(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[A-Za-z0-9._-]+)$/

const passRe = /^[A-Za-z0-9!@#$%^&*._-]+$/

async function loginUser() {
  if (!loginValue.value || !password.value) {
    toast.error('Введите email/логин и пароль')
    return
  }

  if (!loginRe.test(loginValue.value)) {
    toast.error('Некорректный email или логин. Допустимы латиница, цифры и . _ -')
    return
  }

  if (!passRe.test(password.value)) {
    toast.error('Пароль может содержать только латиницу, цифры и !@#$%^&*._-')
    return
  }

  try {
    const payload = {
      user: {},
      password: password.value,
    }
    if (loginValue.value.includes('@')) payload.user.email = loginValue.value
    else payload.user.username = loginValue.value

    const resp = await (await import('../api')).api.post('/auth/login', payload)
    const token = resp?.access_token
    if (!token) throw new Error('No token')

    login(token, loginValue.value)
    toast.success(`Добро пожаловать, ${loginValue.value}!`)
    router.push('/')
  } catch (e) {
    toast.error(e?.message || 'Не удалось войти. Проверьте данные или попробуйте позже.')
  }
}
</script>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.label {
  font-size: 14px;
  color: #666;
}
</style>
