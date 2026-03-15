<template>
  <div class="card p-24" style="max-width:1100px; margin:24px auto">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px">
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
      style="width:100%; height:75vh; min-height:500px; border-radius:14px; overflow:hidden; margin-top:16px"
    ></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { api } from '../api'
import {
  formatBattery,
  getBackendDeviceName,
  getDisplayDeviceName,
  getTenantAccent,
  isBatteryLow,
} from '../devicePresentation'

const mapEl = ref(null)
const error = ref('')
const map = shallowRef(null)
const placemarks = shallowRef([])
const currentTenant = ref({ tenant_id: '', name: 'Текущий тенант' })

function escapeHtml(value) {
  return String(value ?? 'n/a')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

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

function getMarkersFromResponse(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.markers)) return payload.markers
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

function balloon(m) {
  const tenantAccent = getTenantAccent(currentTenant.value.tenant_id || currentTenant.value.name)
  const status = m.online ? 'В сети' : 'Не в сети'
  const displayName = getDisplayDeviceName(m)
  const backendName = getBackendDeviceName(m)
  const battery = formatBattery(m.battery ?? m.battery_level)

  return `
    <div style="
      min-width: 300px;
      padding: 18px;
      border-radius: 22px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      border: 2px solid ${tenantAccent};
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
      color: #0f172a;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
      <div style="font-size:12px; color:${tenantAccent}; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin-bottom:8px;">
        ${escapeHtml(currentTenant.value.name || 'Текущий тенант')}
      </div>
      <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:14px;">
        <div>
          <div style="font-size:19px; font-weight:800; line-height:1.2;">${escapeHtml(displayName)}</div>
          <div style="font-size:13px; color:#64748b; margin-top:4px;">Backend: ${escapeHtml(backendName)}</div>
        </div>
        <div style="padding:6px 10px; border-radius:999px; background:${m.online ? '#dcfce7' : '#fee2e2'}; color:${m.online ? '#15803d' : '#b91c1c'}; font-size:12px; font-weight:700; white-space:nowrap;">
          ${status}
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px;">
        <div style="padding:12px; border-radius:16px; background:#ffffff; border:1px solid rgba(224, 231, 255, 0.95);">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Заряд</div>
          <div style="font-size:16px; font-weight:700;">${escapeHtml(battery)}</div>
        </div>
        <div style="padding:12px; border-radius:16px; background:#ffffff; border:1px solid rgba(224, 231, 255, 0.95);">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Тенант</div>
          <div style="font-size:14px; font-weight:600;">${escapeHtml(currentTenant.value.name || 'Текущий тенант')}</div>
        </div>
        <div style="padding:12px; border-radius:16px; background:#ffffff; border:1px solid rgba(224, 231, 255, 0.95);">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Широта</div>
          <div style="font-size:14px; font-weight:600;">${escapeHtml(m.lat)}</div>
        </div>
        <div style="padding:12px; border-radius:16px; background:#ffffff; border:1px solid rgba(224, 231, 255, 0.95);">
          <div style="font-size:12px; color:#64748b; margin-bottom:4px;">Долгота</div>
          <div style="font-size:14px; font-weight:600;">${escapeHtml(m.lon)}</div>
        </div>
      </div>

      ${isBatteryLow(m.battery ?? m.battery_level)
        ? '<div style="margin-top:12px; padding:10px 12px; border-radius:14px; background:#fff7ed; color:#c2410c; border:1px solid #fdba74; font-weight:600;">Низкий заряд устройства</div>'
        : ''}

      <a href="/management/${encodeURIComponent(m.device_id)}${currentTenant.value.tenant_id ? `?tenant_id=${encodeURIComponent(currentTenant.value.tenant_id)}` : ''}" style="display:inline-flex; margin-top:14px; padding:10px 16px; border-radius:999px; background:#1d4ed8; color:#fff; text-decoration:none; font-weight:700;">
        Открыть управление
      </a>
    </div>
  `
}

async function loadCurrentTenant() {
  try {
    const tenantList = await api.get('/tenants')
    const rows = Array.isArray(tenantList) ? tenantList : []
    currentTenant.value = rows[0] || currentTenant.value
  } catch (e) {
    console.warn('Не удалось загрузить тенанты для карты', e)
  }
}

async function loadMarkers() {
  error.value = ''

  try {
    await ensureMap()
    await loadCurrentTenant()

    const response = await api.get('/map/markers')
    const markers = getMarkersFromResponse(response)

    clearPlacemarks()

    const validMarkers = markers.filter((m) => {
      const lat = Number(m.lat)
      const lon = Number(m.lon)
      return !Number.isNaN(lat) && !Number.isNaN(lon)
    })

    if (!validMarkers.length) {
      error.value = 'Маркеры не найдены'
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
          hintContent: `Устройство: ${escapeHtml(getDisplayDeviceName(m))}`,
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

function handleAliasesChanged() {
  loadMarkers()
}

onMounted(async () => {
  window.addEventListener('pvz-device-aliases-updated', handleAliasesChanged)
  window.addEventListener('storage', handleAliasesChanged)
  await loadMarkers()
})

onBeforeUnmount(() => {
  window.removeEventListener('pvz-device-aliases-updated', handleAliasesChanged)
  window.removeEventListener('storage', handleAliasesChanged)
  clearPlacemarks()
  if (map.value) {
    map.value.destroy()
    map.value = null
  }
})
</script>
