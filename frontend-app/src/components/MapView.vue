<template>
  <div class="card p-24" style="max-width:1100px; margin:24px auto">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap">
      <h2 class="section-title" style="margin:0">Карта</h2>

      <div v-if="error" class="helper" style="color:#b00020">
        {{ error }}
      </div>

      <button class="btn" type="button" @click="loadMarkers">
        Обновить
      </button>
    </div>

<div
  ref="mapEl"
  style="width:100%; height:75vh; min-height:500px; border-radius:14px; overflow:hidden;"
></div>

    <div class="helper mt-12">
      Источник данных: <code>/map/markers</code>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'

const mapEl = ref(null)
const error = ref('')
const map = shallowRef(null)
const placemarks = shallowRef([])

function loadYmaps() {
  if (window.ymaps) return Promise.resolve()

  const key = import.meta.env.VITE_YMAPS_KEY
  if (!key) return Promise.reject(new Error('Не задан VITE_YMAPS_KEY в .env'))

  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.async = true
    s.src = `https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(key)}&lang=ru_RU`
    s.onload = resolve
    s.onerror = () => reject(new Error('Не удалось загрузить Яндекс Карты'))
    document.head.appendChild(s)
  })
}

async function ensureMap() {
  if (map.value) return

  await loadYmaps()
  await new Promise((resolve) => window.ymaps.ready(resolve))

  map.value = new window.ymaps.Map(mapEl.value, {
    center: [52.0907, 5.1214],
    zoom: 7,
    controls: ['zoomControl', 'typeSelector', 'fullscreenControl'],
  })
}

function clearPlacemarks() {
  if (!map.value) return
  for (const pm of placemarks.value) {
    map.value.geoObjects.remove(pm)
  }
  placemarks.value = []
}

function fmt(v) {
  if (v === null || v === undefined || v === '') return 'n/a'
  return String(v)
}

function balloon(m) {
  const status = m.online ? 'online' : 'offline'
  return `
    <div style="min-width:220px">
      <div><strong>Device:</strong> ${fmt(m.device_id)}</div>
      <div><strong>Status:</strong> ${status}</div>
      <div><strong>Battery:</strong> ${fmt(m.battery)}%</div>
      <div><strong>Last seen:</strong> ${fmt(m.last_seen)}</div>
      <div><strong>Lat:</strong> ${fmt(m.lat)}</div>
      <div><strong>Lon:</strong> ${fmt(m.lon)}</div>
    </div>
  `
}

async function loadMarkers() {
  error.value = ''

  try {
    await ensureMap()

    const markers = await api.get('/map/markers')

    clearPlacemarks()

    if (!Array.isArray(markers) || markers.length === 0) return

    const first = markers.find(m => m.lat != null && m.lon != null)
    if (first) {
      map.value.setCenter([Number(first.lat), Number(first.lon)], 14)
    }

    for (const m of markers) {
      const lat = Number(m.lat)
      const lon = Number(m.lon)
      if (isNaN(lat) || isNaN(lon)) continue

      const preset = m.online ? 'islands#greenDotIcon' : 'islands#redDotIcon'

      const pm = new window.ymaps.Placemark(
        [lat, lon],
        {
          hintContent: `Устройство: ${fmt(m.device_id)}`,
          balloonContent: balloon(m),
        },
        { preset }
      )

      map.value.geoObjects.add(pm)
      placemarks.value.push(pm)
    }
  } catch (e) {
    error.value = e?.message || 'Ошибка загрузки карты'
  }
}

onMounted(async () => {
  await loadMarkers()
})

onBeforeUnmount(() => {
  clearPlacemarks()
  if (map.value) {
    map.value.destroy()
    map.value = null
  }
})
</script>