import { ref, computed } from 'vue'

const storedFlag = localStorage.getItem('pvz_is_auth')
const storedEmail = localStorage.getItem('pvz_email')
const storedToken = localStorage.getItem('pvz_token')

const _isAuth = ref(storedFlag === '1')
const _email = ref(storedEmail || '')
const _token = ref(storedToken || '')

export function useAuth() {
  const isAuth = computed(() => _isAuth.value)
  const userEmail = computed(() => _email.value)

  function login(token, email) {
    _isAuth.value = true
    _email.value = email || ''
    _token.value = token || ''
    localStorage.setItem('pvz_is_auth', '1')
    localStorage.setItem('pvz_email', email || '')
    localStorage.setItem('pvz_token', token || '')
  }

  function logout() {
    _isAuth.value = false
    _email.value = ''
    _token.value = ''
    localStorage.removeItem('pvz_is_auth')
    localStorage.removeItem('pvz_email')
    localStorage.removeItem('pvz_token')
  }

  return { isAuth, userEmail, login, logout, token: computed(() => _token.value) }
}
