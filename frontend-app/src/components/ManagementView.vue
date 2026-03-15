<template>
  <div class="management-page">
    <section class="card p-24 toolbar-card">
      <div class="toolbar-head">
        <div>
          <h2 class="section-title" style="margin-bottom:6px">Управление устройствами</h2>
          <div class="helper">Поиск работает и по имени с бэкенда, и по имени, которое пользователь задал на вебе.</div>
        </div>
        <button class="btn" type="button" @click="loadAllDevices" :disabled="loading">
          {{ loading ? 'Обновляем...' : 'Обновить список' }}
        </button>
      </div>

      <div class="toolbar-grid">
        <input
          v-model="search"
          class="input"
          placeholder="Поиск по имени устройства, tenant или device_id"
        />

        <select v-model="tenantFilter" class="select">
          <option value="">Все тенанты</option>
          <option v-for="tenant in tenants" :key="tenant.tenant_id" :value="tenant.tenant_id">
            {{ tenant.name }}
          </option>
        </select>
      </div>
    </section>

    <div v-if="error" class="card p-24 error-card">
      {{ error }}
    </div>

    <section class="devices-grid">
      <article
        v-for="device in filteredDevices"
        :key="device.device_id"
        class="card device-card"
        :style="{ '--tenant-accent': getTenantAccent(device.tenant_id || device.tenant_name) }"
      >
        <div class="device-card__top">
          <div>
            <div class="device-card__eyebrow">{{ device.tenant_name || 'Текущий тенант' }}</div>
            <h3 class="device-card__title">{{ getDisplayDeviceName(device) }}</h3>
            <div class="helper">Backend: {{ getBackendDeviceName(device) }}</div>
          </div>
          <span class="status-pill" :class="device.online ? 'online' : 'offline'">
            {{ device.online ? 'В сети' : 'Не в сети' }}
          </span>
        </div>

        <div class="device-card__meta">
          <div class="meta-box">
            <span class="meta-label">Заряд</span>
            <strong>{{ formatBattery(device.battery) }}</strong>
          </div>
          <div class="meta-box">
            <span class="meta-label">Координаты</span>
            <strong>{{ formatCoords(device) }}</strong>
          </div>
        </div>

        <div v-if="isBatteryLow(device.battery)" class="warning-chip">
          Низкий заряд устройства
        </div>

        <router-link class="btn primary device-card__action" :to="`/management/${device.device_id}?tenant_id=${device.tenant_id}`">
          Открыть карточку
        </router-link>
      </article>
    </section>

    <div v-if="!loading && !filteredDevices.length" class="card p-24 empty-state">
      Устройства не найдены.
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import {
  formatBattery,
  getBackendDeviceName,
  getDisplayDeviceName,
  getTenantAccent,
  isBatteryLow,
  matchesDeviceSearch,
} from '../devicePresentation'

const tenants = ref([])
const devices = ref([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const tenantFilter = ref('')

function formatCoords(device) {
  if (device.lat == null || device.lon == null) return 'n/a'
  return `${Number(device.lat).toFixed(4)}, ${Number(device.lon).toFixed(4)}`
}

const filteredDevices = computed(() => {
  return devices.value.filter((device) => {
    const matchesTenant = !tenantFilter.value || device.tenant_id === tenantFilter.value
    return matchesTenant && matchesDeviceSearch(device, search.value)
  })
})

async function loadAllDevices() {
  loading.value = true
  error.value = ''

  try {
    const tenantList = await api.get('/tenants')
    tenants.value = Array.isArray(tenantList) ? tenantList : []

    const batches = await Promise.all(
      tenants.value.map(async (tenant) => {
        try {
          const result = await api.get(`/devices?tenant_id=${tenant.tenant_id}`)
          const rows = Array.isArray(result) ? result : []
          return rows.map((device) => ({
            ...device,
            tenant_id: tenant.tenant_id,
            tenant_name: tenant.name,
          }))
        } catch (e) {
          console.warn(`Не удалось загрузить устройства tenant ${tenant.name}`, e)
          return []
        }
      })
    )

    devices.value = batches.flat()
  } catch (e) {
    error.value = e?.body?.detail || e?.message || 'Не удалось загрузить устройства'
  } finally {
    loading.value = false
  }
}

onMounted(loadAllDevices)
</script>

<style scoped>
.management-page {
  display: grid;
  gap: 18px;
  margin-top: 24px;
}

.toolbar-card,
.error-card,
.empty-state {
  max-width: 1180px;
  margin: 0 auto;
  width: 100%;
}

.toolbar-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-grid {
  margin-top: 18px;
  display: grid;
  gap: 14px;
  grid-template-columns: minmax(0, 1.4fr) minmax(220px, 0.6fr);
}

.devices-grid {
  max-width: 1180px;
  margin: 0 auto;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
}

.device-card {
  padding: 20px;
  border-radius: 24px;
  border: 2px solid var(--tenant-accent);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.08);
}

.device-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.device-card__eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--tenant-accent);
  font-weight: 700;
  margin-bottom: 6px;
}

.device-card__title {
  margin: 0 0 6px;
  font-size: 22px;
}

.status-pill {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-pill.online {
  background: #dcfce7;
  color: #15803d;
}

.status-pill.offline {
  background: #fee2e2;
  color: #b91c1c;
}

.device-card__meta {
  margin-top: 16px;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.meta-box {
  padding: 14px;
  border-radius: 18px;
  background: #f8fbff;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.meta-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.warning-chip {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fdba74;
  font-weight: 600;
}

.device-card__action {
  margin-top: 16px;
  width: 100%;
}

@media (max-width: 720px) {
  .toolbar-grid,
  .device-card__meta {
    grid-template-columns: 1fr;
  }
}
</style>
