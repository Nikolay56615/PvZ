<script setup>
import { ref, computed } from 'vue'
import ChartsView from './components/ChartsView.vue'
import HomeView from './components/HomeView.vue'

const Devices  = { template: '<div class="card p-24">Управление устройствами — заглушка.</div>' }
const MapView  = { template: '<div class="card p-24">Карта устройств — заглушка.</div>' }
const Settings = { template: '<div class="card p-24">Настройки — заглушка.</div>' }

const tab = ref('home')
const Current = computed(() => ({
  home: HomeView, devices: Devices, map: MapView, charts: ChartsView, settings: Settings
}[tab.value]))
</script>

<template>
  <div class="container">
    <header class="header">
      <div class="brand">
        <div class="logo"></div>
        <h1 class="title">PVZ · Мониторинг влажности</h1>
      </div>
      <nav class="tabs">
        <button class="tab" :class="{active: tab==='home'}"   @click="tab='home'">Главная</button>
        <button class="tab" :class="{active: tab==='charts'}" @click="tab='charts'">Графики</button>
        <button class="tab" :class="{active: tab==='map'}"    @click="tab='map'">Карта</button>
        <button class="tab" :class="{active: tab==='devices'}"@click="tab='devices'">Управление</button>
        <button class="tab" :class="{active: tab==='settings'}"@click="tab='settings'">Настройки</button>
      </nav>
    </header>

    <section>
      <component :is="Current" @go="tab = $event" />
    </section>
  </div>
</template>

<style scoped>
</style>
