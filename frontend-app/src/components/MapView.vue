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

function getMarkersFromResponse(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.markers)) return payload.markers
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

function balloon(m) {
  const status = m.online ? 'В сети' : 'Не в сети'
  const statusColor = m.online ? '#16a34a' : '#ef4444'
  const batteryValue =
    m.battery === null || m.battery === undefined || m.battery === ''
      ? 'n/a'
      : `${fmt(m.battery)}%`

  return `
    <div style="
      min-width: 280px;
      padding: 18px;
      border-radius: 20px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
      border: 1px solid rgba(148, 163, 184, 0.18);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #0f172a;
    ">
      <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:14px;">
        <div>
          <div style="font-size:12px; color:#64748b; margin-bottom:4px; letter-spacing:.04em; text-transform:uppercase;">
            Устройство
          </div>
          <div style="font-size:18px; font-weight:700; line-height:1.2;">
            ${fmt(m.device_id)}
          </div>
        </div>

        <div style="
          padding:6px 10px;
          border-radius:999px;
          background:${m.online ? '#dcfce7' : '#fee2e2'};
          color:${statusColor};
          font-size:12px;
          font-weight:700;
          white-space:nowrap;
        ">
          ${status}
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px;">
        <div style="
          padding:12px;
          border-radius:16px;
          background:#ffffff;
          border:1px solid rgba(224, 231, 255, 0.95);
        ">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Заряд</div>
          <div style="font-size:16px; font-weight:700;">${batteryValue}</div>
        </div>

        <div style="
          padding:12px;
          border-radius:16px;
          background:#ffffff;
          border:1px solid rgba(224, 231, 255, 0.95);
        ">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Последняя активность</div>
          <div style="font-size:14px; font-weight:600; line-height:1.35;">${fmt(m.last_seen)}</div>
        </div>

        <div style="
          padding:12px;
          border-radius:16px;
          background:#ffffff;
          border:1px solid rgba(224, 231, 255, 0.95);
        ">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Широта</div>
          <div style="font-size:14px; font-weight:600;">${fmt(m.lat)}</div>
        </div>

        <div style="
          padding:12px;
          border-radius:16px;
          background:#ffffff;
          border:1px solid rgba(224, 231, 255, 0.95);
        ">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Долгота</div>
          <div style="font-size:14px; font-weight:600;">${fmt(m.lon)}</div>
        </div>
      </div>
    </div>
  `
}

async function loadMarkers() {
  error.value = ''

  try {
    await ensureMap()

    const response = await api.get('/map/markers')
    const markers = getMarkersFromResponse(response)

    clearPlacemarks()

    if (!markers.length) {
      error.value = 'Маркеры не найдены'
      return
    }

    const validMarkers = markers.filter((m) => {
      const lat = Number(m.lat)
      const lon = Number(m.lon)
      return !isNaN(lat) && !isNaN(lon)
    })

    if (!validMarkers.length) {
      error.value = 'В ответе нет корректных координат'
      return
    }

    map.value.setCenter(
      [Number(validMarkers[0].lat), Number(validMarkers[0].lon)],
      validMarkers.length === 1 ? 15 : 12
    )

    for (const m of validMarkers) {
      const lat = Number(m.lat)
      const lon = Number(m.lon)
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
