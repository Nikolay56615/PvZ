import { ref, computed } from 'vue'

const storedFlag = localStorage.getItem('pvz_is_auth')
const storedEmail = localStorage.getItem('pvz_email')

const _isAuth = ref(storedFlag === '1')
const _email = ref(storedEmail || '')

export function useAuth() {
  const isAuth = computed(() => _isAuth.value)
  const userEmail = computed(() => _email.value)

  function login(email) {
    _isAuth.value = true
    _email.value = email
    localStorage.setItem('pvz_is_auth', '1')
    localStorage.setItem('pvz_email', email)
  }

  function logout() {
    _isAuth.value = false
    _email.value = ''
    localStorage.removeItem('pvz_is_auth')
    localStorage.removeItem('pvz_email')
  }

  return { isAuth, userEmail, login, logout }
}
