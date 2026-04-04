<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import Papa from 'papaparse'
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  Tooltip,
  Legend,
  CategoryScale
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { ru } from 'date-fns/locale'

// ВАЖНО:
// если в проекте используется другая библиотека уведомлений,
// замени этот импорт на тот, который уже используется в остальных экранах.
// Например: import { useToast } from 'vue-toastification'
import { toast } from 'vue-sonner'

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  Tooltip,
  Legend,
  CategoryScale
)

/** ---------- utils ---------- */
function parseDate(v) {
  if (v == null || v === '') return null
  const s = String(v)

  // unix sec/ms
  if (/^\d+$/.test(s)) {
    const n = Number(s)
    return s.length === 10 ? n * 1000 : n
  }

  // "YYYY-MM-DD HH:mm(:ss)?"
  if (/\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?/.test(s)) {
    const d = new Date(s.replace(' ', 'T'))
    return isNaN(d) ? null : d.getTime()
  }

  const d = new Date(s)
  return isNaN(d) ? null : d.getTime()
}

function detectCols(fields) {
  const lower = fields.map(x => x.toLowerCase())
  const pick = (...names) => {
    for (const n of names) {
      const i = lower.indexOf(n)
      if (i !== -1) return fields[i]
    }
    return null
  }
  return {
    time: pick('timestamp', 'time', 'datetime', 'date', 'ts', 'sent_ts'),
    hum: pick('humidity_percent', 'humidity', 'humidity_%', 'soil_humidity', 'moisture'),
    temp: pick('temperature', 'temp', 'air_temperature', 'soil_temperature'),
    device: pick('device_id', 'device', 'external_id'),
    loc: pick('location', 'place'),
    lat: pick('lat', 'latitude'),
    lon: pick('lon', 'lng', 'longitude')
  }
}

function toLocalInput(ms) {
  if (ms == null) return ''
  const d = new Date(ms)
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

function isoOrNull(ms) {
  return ms != null ? new Date(ms).toISOString() : null
}

function clampN(v, min, max) {
  const n = Number(v)
  if (!isFinite(n)) return min
  return Math.max(min, Math.min(max, n))
}

function normalizePointTime(x) {
  const d = new Date(x)
  d.setSeconds(0, 0)
  return d.getTime()
}

function formatDateTime24(ms) {
  return new Date(ms).toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

/** ---------- chart ---------- */
const humidityCanvasEl = ref(null)
const temperatureCanvasEl = ref(null)

let humidityChart = null
let temperatureChart = null
let refreshTimer = null

function palette(i) {
  const colors = [
    '#2563eb', '#16a34a', '#dc2626', '#7c3aed', '#ea580c',
    '#0f766e', '#db2777', '#4b5563', '#0891b2', '#a16207'
  ]
  return colors[i % colors.length]
}

const tenants = ref([])
const selectedTenant = ref('')

const devices = ref([])
const selectedDeviceIds = ref([])
const maxSeries = ref(5)

const st = reactive({
  start: null,
  end: null,

  totalPointsBefore: 0,
  totalPointsAfter: 0,

  humiditySeries: [],
  temperatureSeries: [],

  loading: false,
  lastError: null
})

const startLocal = computed({
  get: () => (st.start != null ? toLocalInput(st.start) : ''),
  set: v => {
    st.start = v ? new Date(v).getTime() : null
  }
})

const endLocal = computed({
  get: () => (st.end != null ? toLocalInput(st.end) : ''),
  set: v => {
    st.end = v ? new Date(v).getTime() : null
  }
})

const rangeText = computed(() => {
  const allPts = [
    ...st.humiditySeries.flatMap(s => s.all),
    ...st.temperatureSeries.flatMap(s => s.all)
  ]
  if (!allPts.length) return '—'
  const xs = allPts.map(p => p.x).sort((a, b) => a - b)
  const a = st.start ?? xs[0]
  const b = st.end ?? xs[xs.length - 1]
  const fmt = ms => new Date(ms).toLocaleDateString('ru-RU')
  return `${fmt(a)} — ${fmt(b)}`
})

function buildPointsFromRows(rows, metricKey) {
  if (!rows?.length) return { points: [], meta: { minX: null, maxX: null } }

  const pts = []

  for (const r of rows) {
    let x = parseDate(r.timestamp ?? r.time ?? r.datetime ?? r.date ?? r.ts ?? r.sent_ts)
    const y = Number(r[metricKey])

    if (x == null || !isFinite(y)) continue
    x = normalizePointTime(x)

    let location = 'нет данных'
    if (r.location) {
      location = String(r.location)
    } else if (r.lat != null && r.lon != null) {
      location = `${r.lat}, ${r.lon}`
    }

    pts.push({ x, y, location })
  }

  pts.sort((a, b) => a.x - b.x)

  return {
    points: pts,
    meta: { minX: pts[0]?.x ?? null, maxX: pts[pts.length - 1]?.x ?? null }
  }
}

function applyFilterToSeries() {
  const allPts = [
    ...st.humiditySeries.flatMap(s => s.all),
    ...st.temperatureSeries.flatMap(s => s.all)
  ]

  st.totalPointsBefore = allPts.length

  if (!allPts.length) {
    st.totalPointsAfter = 0
    refreshCharts()
    return
  }

  const xs = allPts.map(p => p.x).sort((a, b) => a - b)
  const a = st.start ?? xs[0]
  const b = st.end ?? xs[xs.length - 1]

  let shown = 0

  for (const s of st.humiditySeries) {
    s.pts = s.all.filter(p => p.x >= a && p.x <= b)
    shown += s.pts.length
  }

  for (const s of st.temperatureSeries) {
    s.pts = s.all.filter(p => p.x >= a && p.x <= b)
    shown += s.pts.length
  }

  st.totalPointsAfter = shown
  refreshCharts()
}

async function preset(kind) {
  const now = Date.now()

  if (kind === '7d') {
    st.start = now - 7 * 24 * 60 * 60 * 1000
    st.end = now
    await loadMultiFromBackend()
    return
  }

  if (kind === '30d') {
    st.start = now - 30 * 24 * 60 * 60 * 1000
    st.end = now
    await loadMultiFromBackend()
    return
  }

  if (kind === 'all') {
    st.start = null
    st.end = now
    await loadMultiFromBackend()
  }
}

async function loadTenants() {
  try {
    const { api } = await import('../api')
    const resp = await api.get('/tenants')
    tenants.value = resp || []
    if (tenants.value.length && !selectedTenant.value) {
      selectedTenant.value = tenants.value[0].tenant_id
    }
  } catch (e) {
    console.warn('Не удалось загрузить тенанты:', e)
  }
}

async function loadDevices() {
  try {
    const { api } = await import('../api')
    const tenantQuery = selectedTenant.value ? `?tenant_id=${selectedTenant.value}` : ''
    const resp = await api.get(`/devices/${tenantQuery}`)
    devices.value = resp || []

    if (devices.value.length) {
      const auto = devices.value.slice(0, clampN(maxSeries.value, 1, 20)).map(d => d.device_id)
      selectedDeviceIds.value = auto
    }
  } catch (e) {
    console.warn('Не удалось загрузить устройства:', e)
  }
}

function makeSeriesLabel(dev) {
  const ext = dev?.external_id ? String(dev.external_id) : ''
  const model = dev?.model ? String(dev.model) : ''
  const base = ext || String(dev.device_id).slice(0, 8)
  return model ? `${base} (${model})` : base
}

function toggleDevice(id) {
  if (selectedDeviceIds.value.includes(id)) {
    selectedDeviceIds.value = selectedDeviceIds.value.filter(x => x !== id)
    return
  }

  if (selectedDeviceIds.value.length >= clampN(maxSeries.value, 1, 20)) {
    toast.error(`Можно выбрать не более ${maxSeries.value} устройств`)
    return
  }

  selectedDeviceIds.value = [...selectedDeviceIds.value, id]
}

// Влажность: путь уже был в проекте
async function fetchHumiditySeries(deviceId, sinceIso, untilIso) {
  const { api } = await import('../api')
  const resp = await api.post(`/charts/humidity/${deviceId}`, { since: sinceIso, until: untilIso })

  return (resp || []).map(r => ({
    timestamp: r.ts || r.sent_ts || r.timestamp,
    humidity: r.humidity,
    location: r.location,
    lat: r.lat,
    lon: r.lon
  }))
}

// Температура: возможно путь на бэке у тебя называется иначе.
// Если backend использует другой endpoint, здесь надо заменить путь.
async function fetchTemperatureSeries(deviceId, sinceIso, untilIso) {
  const { api } = await import('../api')
  const resp = await api.post(`/charts/temperature/${deviceId}`, { since: sinceIso, until: untilIso })

  return (resp || []).map(r => ({
    timestamp: r.ts || r.sent_ts || r.timestamp,
    temperature: r.temperature,
    location: r.location,
    lat: r.lat,
    lon: r.lon
  }))
}

async function loadMultiFromBackend({ silent = false } = {}) {
  const ids = selectedDeviceIds.value.slice(0, clampN(maxSeries.value, 1, 20))
  if (!ids.length) {
    if (!silent) toast.error('Выберите хотя бы одно устройство')
    return
  }

  const now = Date.now()
  const defaultFrom = new Date(now - 7 * 24 * 3600 * 1000).toISOString()
  const defaultTo = new Date(now).toISOString()

  const sinceIso = isoOrNull(st.start) || defaultFrom
  const untilIso = isoOrNull(st.end) || defaultTo

  st.loading = true
  st.lastError = null

  try {
    const devMap = new Map(devices.value.map(d => [d.device_id, d]))

    const results = await Promise.all(
      ids.map(async (id) => {
        const [humidityRows, temperatureRows] = await Promise.all([
          fetchHumiditySeries(id, sinceIso, untilIso),
          fetchTemperatureSeries(id, sinceIso, untilIso)
        ])

        const humidityBuilt = buildPointsFromRows(humidityRows, 'humidity')
        const temperatureBuilt = buildPointsFromRows(temperatureRows, 'temperature')

        return {
          device_id: id,
          label: makeSeriesLabel(devMap.get(id)),
          humidity: humidityBuilt.points,
          temperature: temperatureBuilt.points
        }
      })
    )

    st.humiditySeries = results
      .filter(r => r.humidity.length > 0)
      .map(r => ({
        device_id: r.device_id,
        label: r.label,
        all: r.humidity,
        pts: []
      }))

    st.temperatureSeries = results
      .filter(r => r.temperature.length > 0)
      .map(r => ({
        device_id: r.device_id,
        label: r.label,
        all: r.temperature,
        pts: []
      }))

    const allXs = [
      ...st.humiditySeries.flatMap(s => s.all.map(p => p.x)),
      ...st.temperatureSeries.flatMap(s => s.all.map(p => p.x))
    ].sort((a, b) => a - b)

    if (!allXs.length) {
      st.humiditySeries = []
      st.temperatureSeries = []
      applyFilterToSeries()
      await nextTick()
      drawCharts()
      if (!silent) toast.error('Нет данных по выбранным устройствам за период')
      return
    }

    if (st.start == null) st.start = allXs[0]
    if (st.end == null) st.end = allXs[allXs.length - 1]

    applyFilterToSeries()

    await nextTick()
    drawCharts()
  } catch (e) {
    st.lastError = e?.message || String(e)
    if (!silent) toast.error('Ошибка загрузки данных: ' + st.lastError)
  } finally {
    st.loading = false
  }
}

async function loadCSV(file) {
  if (!file) return

  Papa.parse(file, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
    complete: async res => {
      const rows = res?.data || []
      if (!rows.length) {
        toast.error('CSV пустой')
        return
      }

      const fields = Object.keys(rows[0])
      const c = detectCols(fields)
      if (!c.time || (!c.hum && !c.temp)) {
        toast.error('Нужны колонки времени и хотя бы одна метрика: humidity или temperature')
        return
      }

      if (c.device) {
        const groups = new Map()
        for (const r of rows) {
          const id = String(r[c.device] ?? '').trim()
          if (!id) continue
          if (!groups.has(id)) groups.set(id, [])
          groups.get(id).push({
            timestamp: r[c.time],
            humidity: c.hum ? r[c.hum] : null,
            temperature: c.temp ? r[c.temp] : null,
            location: c.loc ? r[c.loc] : null,
            lat: c.lat ? r[c.lat] : null,
            lon: c.lon ? r[c.lon] : null
          })
        }

        const ids = Array.from(groups.keys()).slice(0, clampN(maxSeries.value, 1, 20))
        const humiditySeries = []
        const temperatureSeries = []

        for (const id of ids) {
          const items = groups.get(id)
          const h = buildPointsFromRows(items, 'humidity')
          const t = buildPointsFromRows(items, 'temperature')

          if (h.points.length) {
            humiditySeries.push({ device_id: id, label: id, all: h.points, pts: [] })
          }
          if (t.points.length) {
            temperatureSeries.push({ device_id: id, label: id, all: t.points, pts: [] })
          }
        }

        st.humiditySeries = humiditySeries
        st.temperatureSeries = temperatureSeries

        const allXs = [
          ...humiditySeries.flatMap(s => s.all.map(p => p.x)),
          ...temperatureSeries.flatMap(s => s.all.map(p => p.x))
        ].sort((a, b) => a - b)

        if (!allXs.length) {
          toast.error('Не удалось построить графики из CSV')
          return
        }

        st.start = allXs[0]
        st.end = allXs[allXs.length - 1]
        applyFilterToSeries()
        await nextTick()
        drawCharts()
        return
      }

      const normalizedRows = rows.map(r => ({
        timestamp: c.time ? r[c.time] : null,
        humidity: c.hum ? r[c.hum] : null,
        temperature: c.temp ? r[c.temp] : null,
        location: c.loc ? r[c.loc] : null,
        lat: c.lat ? r[c.lat] : null,
        lon: c.lon ? r[c.lon] : null
      }))

      const humidityBuilt = buildPointsFromRows(normalizedRows, 'humidity')
      const temperatureBuilt = buildPointsFromRows(normalizedRows, 'temperature')

      st.humiditySeries = humidityBuilt.points.length
        ? [{ device_id: 'csv', label: 'CSV', all: humidityBuilt.points, pts: [] }]
        : []

      st.temperatureSeries = temperatureBuilt.points.length
        ? [{ device_id: 'csv', label: 'CSV', all: temperatureBuilt.points, pts: [] }]
        : []

      const allXs = [
        ...st.humiditySeries.flatMap(s => s.all.map(p => p.x)),
        ...st.temperatureSeries.flatMap(s => s.all.map(p => p.x))
      ].sort((a, b) => a - b)

      if (!allXs.length) {
        toast.error('Нет данных для построения графиков')
        return
      }

      st.start = allXs[0]
      st.end = allXs[allXs.length - 1]
      applyFilterToSeries()
      await nextTick()
      drawCharts()
    }
  })
}

function makeDataset(series, idx) {
  const color = palette(idx)
  return {
    label: series.label,
    data: series.pts,
    parsing: { xAxisKey: 'x', yAxisKey: 'y' },
    tension: 0.25,
    pointRadius: 2.5,
    pointHoverRadius: 6,
    borderWidth: 2.5,
    borderColor: color,
    pointBackgroundColor: color,
    pointBorderColor: color
  }
}

function buildChartOptions(yTitle, yMin = undefined, yMax = undefined) {
  return {
    interaction: { intersect: false, mode: 'nearest' },
    maintainAspectRatio: false,
    scales: {
      x: {
        type: 'time',
        time: {
          tooltipFormat: 'dd.MM.yyyy HH:mm',
          unit: 'hour',
          displayFormats: {
            minute: 'dd.MM HH:mm',
            hour: 'dd.MM HH:mm',
            day: 'dd.MM'
          }
        },
        adapters: { date: { locale: ru } },
        grid: { color: '#eef2f8' },
        ticks: { color: '#3a4b66' }
      },
      y: {
        title: { display: true, text: yTitle, color: '#2b3a55' },
        min: yMin,
        max: yMax,
        grid: { color: '#eef2f8' },
        ticks: { color: '#3a4b66' }
      }
    },
    plugins: {
      legend: { display: true, position: 'bottom' },
      tooltip: {
        callbacks: {
          label: ctx => `${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(1)}`,
          afterLabel: ctx => {
            const p = ctx.raw
            return [`Время: ${formatDateTime24(p.x)}`, `Локация: ${p.location ?? '—'}`]
          }
        }
      }
    }
  }
}

function destroyCharts() {
  if (humidityChart) {
    humidityChart.destroy()
    humidityChart = null
  }
  if (temperatureChart) {
    temperatureChart.destroy()
    temperatureChart = null
  }
}

function drawCharts() {
  destroyCharts()

  if (humidityCanvasEl.value) {
    humidityChart = new Chart(humidityCanvasEl.value.getContext('2d'), {
      type: 'line',
      data: { datasets: st.humiditySeries.map((s, idx) => makeDataset(s, idx)) },
      options: buildChartOptions('Влажность почвы (%)', 0, 100)
    })
  }

  if (temperatureCanvasEl.value) {
    temperatureChart = new Chart(temperatureCanvasEl.value.getContext('2d'), {
      type: 'line',
      data: { datasets: st.temperatureSeries.map((s, idx) => makeDataset(s, idx)) },
      options: buildChartOptions('Температура (°C)')
    })
  }
}

function refreshCharts() {
  if (humidityChart) {
    humidityChart.data.datasets = st.humiditySeries.map((s, idx) => makeDataset(s, idx))
    humidityChart.update('none')
  }

  if (temperatureChart) {
    temperatureChart.data.datasets = st.temperatureSeries.map((s, idx) => makeDataset(s, idx))
    temperatureChart.update('none')
  }
}

function startAutoRefresh() {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    if (!st.loading && selectedDeviceIds.value.length) {
      loadMultiFromBackend({ silent: true })
    }
  }, 30000)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onBeforeUnmount(() => {
  stopAutoRefresh()
  destroyCharts()
})

watch(
  () => [st.start, st.end],
  () => applyFilterToSeries()
)

watch(
  () => selectedTenant.value,
  async () => {
    selectedDeviceIds.value = []
    st.humiditySeries = []
    st.temperatureSeries = []
    st.start = null
    st.end = null
    await loadDevices()
    await loadMultiFromBackend({ silent: true })
  }
)

watch(
  () => maxSeries.value,
  () => {
    const limit = clampN(maxSeries.value, 1, 20)
    if (selectedDeviceIds.value.length > limit) {
      selectedDeviceIds.value = selectedDeviceIds.value.slice(0, limit)
    }
  }
)

onMounted(async () => {
  await loadTenants()
  await loadDevices()

  const now = Date.now()
  st.start = now - 7 * 24 * 60 * 60 * 1000
  st.end = now

  await loadMultiFromBackend({ silent: true })
  startAutoRefresh()
})
</script>

<template>
  <div>
    <div class="card p-24">
      <div class="header-row">
        <h2 class="section-title" style="margin:0">Показания датчиков</h2>

        <div class="top-controls">
          <select class="input select" style="width:auto" v-model="selectedTenant">
            <option value="" disabled>Тенант</option>
            <option v-for="t in tenants" :key="t.tenant_id" :value="t.tenant_id">
              {{ t.name ?? t.tenant_name ?? t.tenant_id }}
            </option>
          </select>

          <select class="input select" style="width:auto" @change="e => preset(e.target.value)">
            <option disabled selected>Выбрать период</option>
            <option value="7d">Последние 7 дней</option>
            <option value="30d">Последние 30 дней</option>
            <option value="all">Весь период</option>
          </select>

          <input
            class="input"
            style="width:90px"
            type="number"
            min="1"
            max="20"
            v-model="maxSeries"
            title="Максимум серий на графике"
          >

          <input
            class="input"
            style="width:auto"
            type="file"
            accept=".csv,text/csv"
            @change="e => loadCSV(e.target.files?.[0])"
          />

          <button class="btn" :disabled="st.loading" @click="loadMultiFromBackend()">
            {{ st.loading ? 'Обновление…' : 'Обновить' }}
          </button>
        </div>
      </div>

      <div class="filters-row">
        <div class="devices-col">
          <div class="helper">Устройства</div>

          <div class="devices-box">
            <label
              v-for="d in devices"
              :key="d.device_id"
              class="device-item"
              @click.prevent="toggleDevice(d.device_id)"
            >
              <input
                type="checkbox"
                :checked="selectedDeviceIds.includes(d.device_id)"
                @change.prevent
              />
              <span>{{ (d.external_id ?? d.device_id) }}{{ d.model ? ` • ${d.model}` : '' }}</span>
            </label>
          </div>

          <div class="helper" style="margin-top:6px;">
            Выбрано: {{ selectedDeviceIds.length }} (на график попадёт до {{ maxSeries }})
          </div>
        </div>

        <div class="range-row">
          <div>
            <div class="helper">Начало</div>
            <input class="input" type="datetime-local" v-model="startLocal" />
          </div>
          <div>
            <div class="helper">Конец</div>
            <input class="input" type="datetime-local" v-model="endLocal" />
          </div>
        </div>
      </div>

      <div class="charts-grid mt-20">
        <div class="chart-card">
          <div class="chart-title">Влажность</div>
          <div class="chart-wrap">
            <div v-if="!st.humiditySeries.length || !st.humiditySeries.some(s => s.pts?.length)" class="empty">
              Нет данных по влажности
            </div>
            <canvas v-else ref="humidityCanvasEl"></canvas>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-title">Температура</div>
          <div class="chart-wrap">
            <div v-if="!st.temperatureSeries.length || !st.temperatureSeries.some(s => s.pts?.length)" class="empty">
              Нет данных по температуре
            </div>
            <canvas v-else ref="temperatureCanvasEl"></canvas>
          </div>
        </div>
      </div>

      <div class="helper" style="text-align:center; margin-top:12px">
        Общие фильтры применяются к обоим графикам
      </div>
    </div>

    <div class="card stats-bar p-24 mt-20">
      <div class="stats-grid">
        <div class="stat">
          <div class="stat-k">Серий на графиках</div>
          <div class="stat-v">{{ Math.max(st.humiditySeries.length, st.temperatureSeries.length) }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">Точек до фильтра</div>
          <div class="stat-v">{{ st.totalPointsBefore }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">Точек после фильтра</div>
          <div class="stat-v">{{ st.totalPointsAfter }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">Диапазон</div>
          <div class="stat-v">{{ rangeText }}</div>
        </div>
      </div>

      <div v-if="st.lastError" class="mt-12" style="color:#b91c1c;">
        Ошибка: {{ st.lastError }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.btn {
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #fff;
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.mt-12 { margin-top: 12px; }
.mt-20 { margin-top: 20px; }

.header-row {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:16px;
  flex-wrap:wrap;
}

.top-controls {
  display:flex;
  gap:10px;
  align-items:center;
  flex-wrap:wrap;
}

.filters-row {
  margin-top:16px;
  display:flex;
  gap:12px;
  flex-wrap:wrap;
  align-items:flex-end;
}

.devices-col {
  min-width: 260px;
  flex:1;
}

.devices-box {
  width: 100%;
  min-height: 180px;
  max-height: 240px;
  overflow: auto;
  border: 1px solid #d7deea;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
}

.device-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 6px;
  cursor: pointer;
  user-select: none;
}

.device-item + .device-item {
  border-top: 1px solid #eef2f8;
}

.range-row {
  display:flex;
  gap:12px;
  flex-wrap:wrap;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  border: 1px solid #eef2f8;
  border-radius: 14px;
  padding: 12px;
  background: #fff;
}

.chart-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.chart-wrap {
  height: 460px;
}

.empty {
  height: 100%;
  display: grid;
  place-items: center;
  text-align: center;
  color: #64748b;
}

@media (max-width: 1100px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>

