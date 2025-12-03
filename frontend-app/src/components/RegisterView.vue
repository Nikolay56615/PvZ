<template>
  <div class="card p-28" style="max-width:420px; margin:40px auto">
    <h2 class="section-title" style="text-align:center">Регистрация</h2>

    <div class="form">
      <label class="label">Email</label>
      <input
        class="input"
        v-model="email"
        type="email"
        placeholder="you@example.com"
      />

      <label class="label">Пароль</label>
      <input
        class="input"
        v-model="password"
        type="password"
        placeholder="••••••••"
      />

      <label class="label">Повтор пароля</label>
      <input
        class="input"
        v-model="password2"
        type="password"
        placeholder="••••••••"
      />

      <button class="btn primary mt-20" type="button" @click="registerUser">
        Создать аккаунт
      </button>

      <div class="helper" style="margin-top:12px; text-align:center">
        Уже есть аккаунт?
        <router-link to="/login">Войти</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useToast } from 'vue-toastification'
import { useRouter } from 'vue-router'

const toast = useToast()
const router = useRouter()

const email = ref('')
const password = ref('')
const password2 = ref('')

const emailRe = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/
const passRe = /^[A-Za-z0-9!@#$%^&*._-]+$/

async function registerUser() {
  if (!email.value || !password.value || !password2.value) {
    toast.error('Заполни все поля')
    return
  }

  if (!emailRe.test(email.value)) {
    toast.error('Некорректный email. Допустимы только латиница, цифры и ._%+-')
    return
  }

  if (!passRe.test(password.value) || !passRe.test(password2.value)) {
    toast.error('Пароль может содержать только латиницу, цифры и !@#$%^&*._-')
    return
  }

  if (password.value !== password2.value) {
    toast.error('Пароли не совпадают')
    return
  }

  try {
    // Здесь должен быть запрос к бэкенду для регистрации:
    // await api.post('/auth/register', { email: email.value, password: password.value })

    toast.success('Аккаунт создан. Теперь войди.')
    router.push('/login')
  } catch (e) {
    toast.error('Не удалось создать аккаунт. Попробуйте позже.')
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
