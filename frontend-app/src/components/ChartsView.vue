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

/** ---------- chart ---------- */
const canvasEl = ref(null)
let chart

function palette(i) {
  // без внешних зависимостей: простая, но различимая палитра
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

  totalPoints: 0,
  totalPointsShown: 0,

  series: [], 
  loading: false,
  lastError: null
})

const seriesCache = new Map()

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
  const allPts = st.series.flatMap(s => s.all)
  if (!allPts.length) return '—'
  const xs = allPts.map(p => p.x).sort((a, b) => a - b)
  const a = st.start ?? xs[0]
  const b = st.end ?? xs[xs.length - 1]
  const fmt = ms => new Date(ms).toLocaleDateString('ru-RU')
  return `${fmt(a)} — ${fmt(b)}`
})

const selectedDevicesResolved = computed(() => {
  const map = new Map(devices.value.map(d => [d.device_id, d]))
  return selectedDeviceIds.value.map(id => map.get(id)).filter(Boolean)
})

function buildPointsFromRows(rows) {
  if (!rows?.length) return { points: [], meta: { minX: null, maxX: null } }

  const fields = Object.keys(rows[0])
  const c = detectCols(fields)
  if (!c.time || !c.hum) {
    throw new Error('Нужны колонки времени и влажности (timestamp + humidity)')
  }

  const pts = []
  for (const r of rows) {
    let x = parseDate(r[c.time])
    const y = Number(r[c.hum])
    if (x == null || !isFinite(y)) continue

    const d = new Date(x)
    d.setSeconds(0, 0)
    x = d.getTime()

    let location = 'нет данных'
    if (c.loc && r[c.loc]) {
      location = String(r[c.loc])
    } else if (c.lat && c.lon && r[c.lat] != null && r[c.lon] != null) {
      location = `${r[c.lat]}, ${r[c.lon]}`
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
  const allPts = st.series.flatMap(s => s.all)
  st.totalPoints = allPts.length

  if (!allPts.length) {
    st.totalPointsShown = 0
    refresh()
    return
  }

  const xs = allPts.map(p => p.x).sort((a, b) => a - b)
  const a = st.start ?? xs[0]
  const b = st.end ?? xs[xs.length - 1]

  let shown = 0
  for (const s of st.series) {
    s.pts = s.all.filter(p => p.x >= a && p.x <= b)
    shown += s.pts.length
  }
  st.totalPointsShown = shown

  refresh()
}

function preset(kind) {
  const allPts = st.series.flatMap(s => s.all)
  if (!allPts.length) return

  const xs = allPts.map(p => p.x).sort((a, b) => a - b)
  const end = xs[xs.length - 1]
  let start = xs[0]

  if (kind === '7d') {
    const d = new Date(end)
    d.setDate(d.getDate() - 7)
    d.setSeconds(0, 0)
    start = d.getTime()
  }
  if (kind === '30d') {
    const d = new Date(end)
    d.setDate(d.getDate() - 30)
    d.setSeconds(0, 0)
    start = d.getTime()
  }
  if (kind === 'all') {
    st.start = xs[0]
    st.end = end
    applyFilterToSeries()
    return
  }

  st.start = start
  st.end = end
  applyFilterToSeries()
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

async function fetchHumiditySeries(deviceId, sinceIso, untilIso) {
  const cacheKey = `${deviceId}|${sinceIso}|${untilIso}`
  if (seriesCache.has(cacheKey)) return seriesCache.get(cacheKey)

  const { api } = await import('../api')
  const resp = await api.post(`/charts/humidity/${deviceId}`, { since: sinceIso, until: untilIso })
  const rows = (resp || []).map(r => ({
    timestamp: r.ts || r.sent_ts,
    humidity_percent: r.humidity
  }))
  seriesCache.set(cacheKey, rows)
  return rows
}

async function loadMultiFromBackend() {
  const ids = selectedDeviceIds.value.slice(0, clampN(maxSeries.value, 1, 20))
  if (!ids.length) {
    alert('Выберите хотя бы одно устройство')
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
        const rows = await fetchHumiditySeries(id, sinceIso, untilIso)
        const { points, meta } = buildPointsFromRows(rows)
        return {
          device_id: id,
          label: makeSeriesLabel(devMap.get(id)),
          all: points,
          pts: [],
          minX: meta.minX,
          maxX: meta.maxX
        }
      })
    )

    const nonEmpty = results.filter(r => r.all.length > 0)

    if (!nonEmpty.length) {
      alert('Нет данных по выбранным устройствам за период')
      st.series = []
      applyFilterToSeries()
      await nextTick()
      draw()
      return
    }

    const allXs = nonEmpty.flatMap(s => s.all.map(p => p.x)).sort((a, b) => a - b)
    if (st.start == null) st.start = allXs[0]
    if (st.end == null) st.end = allXs[allXs.length - 1]

    st.series = nonEmpty
    applyFilterToSeries()

    await nextTick()
    draw()
  } catch (e) {
    st.lastError = e?.message || String(e)
    alert('Ошибка загрузки данных: ' + st.lastError)
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
        alert('CSV пустой')
        return
      }

      const fields = Object.keys(rows[0])
      const c = detectCols(fields)
      if (!c.time || !c.hum) {
        alert('Нужны колонки времени и влажности (timestamp + humidity)')
        return
      }

      if (c.device) {
        const groups = new Map()
        for (const r of rows) {
          const id = String(r[c.device] ?? '').trim()
          if (!id) continue
          if (!groups.has(id)) groups.set(id, [])
          groups.get(id).push(r)
        }
        const ids = Array.from(groups.keys()).slice(0, clampN(maxSeries.value, 1, 20))
        const resultSeries = []
        for (const id of ids) {
          const { points, meta } = buildPointsFromRows(groups.get(id))
          if (points.length) {
            resultSeries.push({ device_id: id, label: id, all: points, pts: [], minX: meta.minX, maxX: meta.maxX })
          }
        }
        if (!resultSeries.length) {
          alert('Не удалось построить графики из CSV')
          return
        }
        const allXs = resultSeries.flatMap(s => s.all.map(p => p.x)).sort((a, b) => a - b)
        st.series = resultSeries
        st.start = allXs[0]
        st.end = allXs[allXs.length - 1]
        applyFilterToSeries()
        await nextTick()
        draw()
        return
      }

      const { points, meta } = buildPointsFromRows(rows)
      if (!points.length) {
        alert('Нет данных для построения графика')
        return
      }
      st.series = [{
        device_id: 'csv',
        label: 'CSV',
        all: points,
        pts: []
      }]
      st.start = meta.minX
      st.end = meta.maxX
      applyFilterToSeries()
      await nextTick()
      draw()
    }
  })
}

function draw() {
  if (!canvasEl.value) return

  if (chart) chart.destroy()

  const datasets = st.series.map((s, idx) => {
    const color = palette(idx)
    return {
      label: s.label,
      data: s.pts,
      parsing: { xAxisKey: 'x', yAxisKey: 'y' },
      tension: 0.25,
      pointRadius: 2.5,
      pointHoverRadius: 6,
      borderWidth: 2.5,
      borderColor: color,
      pointBackgroundColor: color,
      pointBorderColor: color
    }
  })

  chart = new Chart(canvasEl.value.getContext('2d'), {
    type: 'line',
    data: { datasets },
    options: {
      interaction: { intersect: false, mode: 'nearest' },
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: {
            tooltipFormat: 'dd.MM.yyyy HH:mm',
            unit: 'minute',
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
          title: { display: true, text: 'Влажность почвы (%)', color: '#2b3a55' },
          min: 0,
          max: 100,
          grid: { color: '#eef2f8' },
          ticks: { color: '#3a4b66' }
        }
      },
      plugins: {
        legend: { display: true, position: 'bottom' },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(1)}%`,
            afterLabel: ctx => {
              const p = ctx.raw
              const dt = new Date(p.x).toLocaleString('ru-RU', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              })
              return [`Время: ${dt}`, `Локация: ${p.location ?? '—'}`]
            }
          }
        }
      }
    }
  })
}

function refresh() {
  if (!chart) return

  if (chart.data.datasets.length !== st.series.length) {
    draw()
    return
  }

  st.series.forEach((s, idx) => {
    chart.data.datasets[idx].label = s.label
    chart.data.datasets[idx].data = s.pts
  })
  chart.update('none')
}

onBeforeUnmount(() => {
  if (chart) chart.destroy()
})

watch(
  () => [st.start, st.end],
  () => applyFilterToSeries()
)

watch(
  () => selectedTenant.value,
  async () => {
    selectedDeviceIds.value = []
    st.series = []
    st.start = null
    st.end = null
    seriesCache.clear()
    await loadDevices()
  }
)

onMounted(async () => {
  await loadTenants()
  await loadDevices()
})
</script>

<template>
  <div>
    <div class="card p-24">
      <div
        style="display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;"
      >
        <h2 class="section-title" style="margin:0">Показания датчиков</h2>

        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <select class="input select" style="width:auto" v-model="selectedTenant">
            <option value="" disabled>Тенант</option>
            <option v-for="t in tenants" :key="t.tenant_id" :value="t.tenant_id">
              {{ t.name ?? t.tenant_name ?? t.tenant_id }}
            </option>
          </select>

          <select class="input select" style="width:auto" @change="e => preset(e.target.value)">
            <option disabled selected>Выбрать период</option>
            <option value="7d">Последняя неделя</option>
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

          <button class="btn" :disabled="st.loading" @click="loadMultiFromBackend">
            {{ st.loading ? 'Загрузка…' : 'Обновить' }}
          </button>
        </div>
      </div>

      <div class="mt-16" style="display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end;">
        <div style="min-width:260px; flex:1;">
          <div class="helper">Устройства (выборочно)</div>
          <select
            class="input select"
            multiple
            size="6"
            v-model="selectedDeviceIds"
            style="width:100%; min-height:140px;"
          >
            <option v-for="d in devices" :key="d.device_id" :value="d.device_id">
              {{ (d.external_id ?? d.device_id) }}{{ d.model ? ` • ${d.model}` : '' }}
            </option>
          </select>
          <div class="helper" style="margin-top:6px;">
            Выбрано: {{ selectedDeviceIds.length }} (на график попадёт до {{ maxSeries }})
          </div>
        </div>

        <div class="range-row" style="display:flex; gap:12px; flex-wrap:wrap;">
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

      <div class="mt-20" style="height:460px">
        <div v-if="!st.series.length || !st.series.some(s => s.pts?.length)" class="empty">
          Данные пока не загружены.<br />
          Выберите устройства и нажмите “Обновить” или импортируйте CSV.
        </div>
        <canvas v-else ref="canvasEl"></canvas>
      </div>

      <div class="helper" style="text-align:center; margin-top:12px">
        Влажность почвы (несколько устройств)
      </div>
    </div>

    <div class="card stats-bar p-24 mt-20">
      <div class="stats-grid">
        <div class="stat">
          <div class="stat-k">Серий на графике</div>
          <div class="stat-v">{{ st.series.length }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">Точек всего</div>
          <div class="stat-v">{{ st.totalPoints }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">После фильтра</div>
          <div class="stat-v">{{ st.totalPointsShown }}</div>
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
.mt-16 { margin-top: 16px; }
.mt-20 { margin-top: 20px; }
</style>
