<script setup>
</script>

<template>
  <div class="card p-28">
    <div style="display:flex; justify-content:flex-end; gap:20px; margin-bottom:8px">
      <a href="#" class="helper">Войти</a>
      <a href="#" class="helper">Регистрация</a>
    </div>

    <div class="hero">
      <h2>Добро пожаловать</h2>
      <p>Это IoT-система для мониторинга влажности почвы.</p>
      <div class="actions">
        <a class="btn primary" href="javascript:void(0)" @click="$emit('go','charts')">ГРАФИК</a>
        <a class="btn" href="javascript:void(0)" @click="$emit('go','map')">КАРТА</a>
        <a class="btn" href="javascript:void(0)" @click="$emit('go','devices')">УПРАВЛЕНИЕ</a>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
