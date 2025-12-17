<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
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

function parseDate(v) {
  if (v == null || v === '') return null
  const s = String(v)

  if (/^\d+$/.test(s)) {
    const n = Number(s)
    return s.length === 10 ? n * 1000 : n
  }

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
    time: pick('timestamp', 'time', 'datetime', 'date'),
    hum: pick('humidity_percent', 'humidity', 'humidity_%', 'soil_humidity', 'moisture'),
    loc: pick('location', 'place'),
    lat: pick('lat', 'latitude'),
    lon: pick('lon', 'lng', 'longitude')
  }
}

function toLocalInput(ms) {
  if (ms == null) return ''
  const d = new Date(ms)
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(
    d.getHours()
  )}:${p(d.getMinutes())}`
}

const canvasEl = ref(null)
let chart

const devices = ref([])
const selectedDevice = ref('')
const tenants = ref([])
const selectedTenant = ref('')

const st = reactive({
  rows: [],
  all: [],
  pts: [],
  start: null,
  end: null
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
  if (!st.all.length) return '—'
  const a = st.start ?? st.all[0].x
  const b = st.end ?? st.all[st.all.length - 1].x
  const fmt = ms => new Date(ms).toLocaleDateString('ru-RU')
  return `${fmt(a)} — ${fmt(b)}`
})

async function processRows(rows) {
  if (!rows.length) {
    alert('Нет данных для построения графика')
    return
  }

  const fields = Object.keys(rows[0])
  const c = detectCols(fields)
  if (!c.time || !c.hum) {
    alert('Нужны колонки времени и влажности')
    return
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

  st.rows = rows
  st.all = pts
  st.start = pts[0]?.x ?? null
  st.end = pts[pts.length - 1]?.x ?? null

  applyFilter()
  await nextTick()
  draw()
}

function loadCSV(file) {
  if (!file) return

  Papa.parse(file, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
    complete: async res => {
      const rows = res?.data || []
      await processRows(rows)
    }
  })
}

async function loadFromBackend(options = {}) {
  const deviceId = options.deviceId || selectedDevice.value
  if (!deviceId) {
    alert('Выберите устройство для загрузки данных')
    return
  }

  const from = options.from ?? (st.start ? new Date(st.start).toISOString() : null)
  const to = options.to ?? (st.end ? new Date(st.end).toISOString() : null)

  const useFrom = from || new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString()
  const useTo = to || new Date().toISOString()

  try {
    const { api } = await import('../api')
    const resp = await api.post(`/charts/humidity/${deviceId}`, { since: useFrom, until: useTo })
    const rows = (resp || []).map(r => ({ timestamp: r.ts || r.sent_ts, humidity_percent: r.humidity }))
    if (!rows.length) {
      alert('Нет данных за выбранный период')
      return
    }
    await processRows(rows)
  } catch (e) {
    alert('Ошибка загрузки данных: ' + (e?.message || e))
  }
}

async function loadDevices() {
  try {
    const { api } = await import('../api')
    const tenantQuery = selectedTenant.value ? `?tenant_id=${selectedTenant.value}` : ''
    const resp = await api.get(`/devices/${tenantQuery}`)
    devices.value = resp || []
    if (devices.value.length) selectedDevice.value = devices.value[0].device_id
  } catch (e) {
    console.warn('Не удалось загрузить устройства:', e)
  }
}

async function loadTenants() {
  try {
    const { api } = await import('../api')
    const resp = await api.get('/tenants')
    tenants.value = resp || []
    if (tenants.value.length && !selectedTenant.value) selectedTenant.value = tenants.value[0].tenant_id
  } catch (e) {
    console.warn('Не удалось загрузить тенанты:', e)
  }
}

function applyFilter() {
  if (!st.all.length) {
    st.pts = []
    refresh()
    return
  }
  const a = st.start ?? st.all[0].x
  const b = st.end ?? st.all[st.all.length - 1].x
  st.pts = st.all.filter(p => p.x >= a && p.x <= b)
  refresh()
}

function preset(kind) {
  if (!st.all.length) return
  const end = st.all[st.all.length - 1].x
  let start = st.all[0].x

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
    st.start = st.all[0].x
    st.end = end
    applyFilter()
    return
  }
  st.start = start
  st.end = end
  applyFilter()
}

function draw() {
  if (!canvasEl.value) return

  if (chart) chart.destroy()

  chart = new Chart(canvasEl.value.getContext('2d'), {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Влажность, %',
          data: st.pts,
          parsing: { xAxisKey: 'x', yAxisKey: 'y' },
          tension: 0.25,
          pointRadius: 3,
          pointHoverRadius: 6,
          borderWidth: 3,
          borderColor: '#2563eb',
          pointBackgroundColor: '#2563eb',
          pointBorderColor: '#2563eb'
        }
      ]
    },
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
          adapters: {
            date: { locale: ru }
          },
          grid: { color: '#eef2f8' },
          ticks: { color: '#3a4b66' }
        },
        y: {
          title: {
            display: true,
            text: 'Влажность почвы (%)',
            color: '#2b3a55'
          },
          min: 0,
          max: 100,
          grid: { color: '#eef2f8' },
          ticks: { color: '#3a4b66' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `Влажность: ${Number(ctx.parsed.y).toFixed(1)}%`,
            afterLabel: ctx => {
              const p = ctx.raw
              const dt = new Date(p.x).toLocaleString('ru-RU', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              })
              return [`Время: ${dt}`, `Локация: ${p.location}`]
            }
          }
        }
      }
    }
  })
}

function refresh() {
  if (!chart) return
  chart.data.datasets[0].data = st.pts
  chart.update('none')
}

watch(
  () => [st.start, st.end],
  applyFilter
)

onMounted(() => {
  loadTenants()
  loadDevices()
})
</script>

<template>
  <div>
    <div class="card p-24">
      <div
        style="
          display:flex;
          justify-content:space-between;
          align-items:center;
          gap:16px;
          flex-wrap:wrap;
        "
      >
        <h2 class="section-title" style="margin:0">Показания датчиков</h2>
        <div
          style="
            display:flex;
            gap:10px;
            align-items:center;
            flex-wrap:wrap;
          "
        >
          <select class="input select" style="width:auto" v-model="selectedTenant" @change="loadDevices">
            <option value="" disabled selected>Тенант</option>
            <option v-for="t in tenants" :key="t.tenant_id" :value="t.tenant_id">{{ t.name }}</option>
          </select>

          <select class="input select" style="width:auto" @change="e => preset(e.target.value)">
            <option disabled selected>Выбрать период</option>
            <option value="7d">Последняя неделя</option>
            <option value="30d">Последние 30 дней</option>
            <option value="all">Весь период</option>
          </select>
          <input
            class="input"
            style="width:auto"
            type="file"
            accept=".csv,text/csv"
            @change="e => loadCSV(e.target.files?.[0])"
          >
        </div>
      </div>

      <div class="mt-20" style="height:460px">
        <div v-if="!st.pts.length" class="empty">
        Данные пока не загружены. Импортируйте CSV или выберите период для просмотра измерений.<br>
        </div>
        <canvas v-else ref="canvasEl"></canvas>
      </div>

      <div class="helper" style="text-align:center; margin-top:12px">
        Влажность почвы
      </div>
    </div>

    <div class="card stats-bar p-24 mt-20">
      <div class="stats-grid">
        <div class="stat">
          <div class="stat-k">Точек всего</div>
          <div class="stat-v">{{ st.rows.length }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">После фильтра</div>
          <div class="stat-v">{{ st.pts.length }}</div>
        </div>
        <div class="stat">
          <div class="stat-k">Диапазон</div>
          <div class="stat-v">{{ rangeText }}</div>
        </div>
      </div>

      <div class="range-row mt-20">
        <div>
          <div class="helper">Начало</div>
          <input class="input" type="datetime-local" v-model="startLocal">
        </div>
        <div>
          <div class="helper">Конец</div>
          <input class="input" type="datetime-local" v-model="endLocal">
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
