<template>
  <div class="card p-28" style="margin-top:20px">
    <div v-if="!isAuth" class="hero">
      <h2>PVZ · мониторинг влажности</h2>
      <p>
        Это IoT-система для мониторинга влажности почвы.
        Чтобы продолжить, войдите в систему или зарегистрируйтесь.
      </p>

      <div class="actions">
        <router-link
          class="btn primary"
          style="min-width:220px; font-size:18px"
          to="/login"
        >
          ВОЙТИ
        </router-link>

        <router-link
          class="btn"
          style="min-width:220px; font-size:18px"
          to="/register"
        >
          РЕГИСТРАЦИЯ
        </router-link>
      </div>
    </div>

    <div v-else class="hero">
      <h2>Добро пожаловать</h2>
      <p>Это IoT-система для мониторинга влажности почвы.</p>
    </div>
  </div>
</template>

<script setup>
import { useAuth } from '../auth'

const { isAuth } = useAuth()
</script>

<style scoped>
</style>
