<template>
  <div class="device-page" v-if="device">
    <section class="card p-24 device-shell" :style="{ '--tenant-accent': getTenantAccent(device.tenant_id || device.tenant_name) }">
      <div class="device-shell__head">
        <div>
          <div class="device-shell__eyebrow">{{ device.tenant_name || 'Текущий тенант' }}</div>
          <h2 class="section-title device-shell__title">{{ displayName }}</h2>
          <div class="helper">Backend: {{ backendName }}</div>
        </div>
        <router-link to="/management" class="btn">К списку устройств</router-link>
      </div>

      <div class="device-shell__grid">
        <div class="info-box">
          <span class="info-label">Имя устройства</span>
          <strong>{{ displayName }}</strong>
        </div>
        <div class="info-box">
          <span class="info-label">Заряд</span>
          <strong>{{ formatBattery(device.battery) }}</strong>
          <div v-if="isBatteryLow(device.battery)" class="warning-chip mt-10">Низкий заряд, стоит проверить устройство</div>
        </div>
        <div class="info-box">
          <span class="info-label">Местоположение</span>
          <strong>{{ coordsText }}</strong>
        </div>
        <div class="info-box">
          <span class="info-label">Тенант</span>
          <strong>{{ device.tenant_name || 'Текущий тенант' }}</strong>
        </div>
        <div class="info-box">
          <span class="info-label">Статус</span>
          <strong>{{ device.online ? 'В сети' : 'Не в сети' }}</strong>
        </div>
        <div class="info-box">
          <span class="info-label">Последнее обновление координат</span>
          <strong>{{ locationUpdatedAt }}</strong>
        </div>
      </div>
    </section>

    <section class="device-layout">
      <div class="card p-24">
        <h3 class="section-title">Действия</h3>
        <div class="actions-grid">
          <button class="btn primary" type="button" :disabled="pendingCommand === 'power_on'" @click="sendCommand('power_on')">
            {{ pendingCommand === 'power_on' ? 'Отправляем...' : 'Включить устройство' }}
          </button>
          <button class="btn" type="button" :disabled="pendingCommand === 'power_off'" @click="sendCommand('power_off')">
            {{ pendingCommand === 'power_off' ? 'Отправляем...' : 'Выключить устройство' }}
          </button>
          <button class="btn" type="button" :disabled="pendingCommand === 'refresh'" @click="sendCommand('refresh')">
            {{ pendingCommand === 'refresh' ? 'Запрашиваем...' : 'Запросить свежие данные' }}
          </button>
        </div>
        <div class="helper" style="margin-top:12px">
          Команды сейчас отправляются как <code>power_on</code>, <code>power_off</code> и <code>refresh</code>. Если на бэкенде ожидаются другие типы, поменяй их в одном месте внутри <code>sendCommand</code>.
        </div>
      </div>

      <div class="card p-24">
        <h3 class="section-title">Имя для веба</h3>
        <div class="helper">Это переименование только для интерфейса. Данные на бэкенде не меняются.</div>
        <input v-model="draftAlias" class="input" style="margin-top:14px" placeholder="Новое имя устройства" />
        <div class="rename-actions">
          <button class="btn primary" type="button" @click="saveAlias">Сохранить имя</button>
          <button class="btn" type="button" @click="resetAlias">Сбросить имя</button>
        </div>
      </div>
    </section>
  </div>

  <div v-else class="card p-24" style="max-width:980px; margin:24px auto">
    {{ loading ? 'Загрузка устройства...' : (error || 'Устройство не найдено') }}
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { api } from '../api'
import {
  formatBattery,
  getBackendDeviceName,
  getDeviceAlias,
  getDisplayDeviceName,
  getTenantAccent,
  isBatteryLow,
  setDeviceAlias,
} from '../devicePresentation'

const route = useRoute()
const toast = useToast()

const device = ref(null)
const loading = ref(false)
const error = ref('')
const draftAlias = ref('')
const pendingCommand = ref('')

const deviceId = computed(() => String(route.params.deviceId || ''))
const tenantId = computed(() => String(route.query.tenant_id || ''))

const backendName = computed(() => (device.value ? getBackendDeviceName(device.value) : ''))
const displayName = computed(() => (device.value ? getDisplayDeviceName(device.value) : ''))
const coordsText = computed(() => {
  if (!device.value || device.value.lat == null || device.value.lon == null) return 'n/a'
  return `${Number(device.value.lat).toFixed(5)}, ${Number(device.value.lon).toFixed(5)}`
})
const locationUpdatedAt = computed(() => {
  const value = device.value?.location_updated_at
  if (!value) return 'n/a'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString('ru-RU')
})

async function loadDevice() {
  loading.value = true
  error.value = ''
  try {
    const tenants = await api.get('/tenants')
    const tenantList = Array.isArray(tenants) ? tenants : []

    let targetTenantId = tenantId.value
    if (!targetTenantId) {
      const foundById = tenantList.find((tenant) => tenant.tenant_id === tenantId.value)
      targetTenantId = foundById?.tenant_id || tenantList[0]?.tenant_id || ''
    }

    const requests = targetTenantId
      ? [targetTenantId]
      : tenantList.map((tenant) => tenant.tenant_id)

    for (const currentTenantId of requests) {
      const list = await api.get(`/devices?tenant_id=${currentTenantId}`)
      const match = (Array.isArray(list) ? list : []).find((item) => item.device_id === deviceId.value)
      if (match) {
        const tenant = tenantList.find((item) => item.tenant_id === currentTenantId)
        device.value = {
          ...match,
          tenant_id: currentTenantId,
          tenant_name: tenant?.name || 'Текущий тенант',
        }
        draftAlias.value = getDeviceAlias(match.device_id)
        return
      }
    }

    error.value = 'Не удалось найти устройство'
  } catch (e) {
    error.value = e?.body?.detail || e?.message || 'Ошибка загрузки устройства'
  } finally {
    loading.value = false
  }
}

async function sendCommand(type) {
  if (!device.value) return
  pendingCommand.value = type
  try {
    const query = device.value.tenant_id ? `?tenant_id=${device.value.tenant_id}` : ''
    await api.post(`/devices/${device.value.device_id}/command${query}`, {
      type,
      params: {},
      retain: false,
    })
    toast.success('Команда отправлена')
  } catch (e) {
    toast.error(e?.body?.detail || e?.message || 'Не удалось отправить команду')
  } finally {
    pendingCommand.value = ''
  }
}

function saveAlias() {
  if (!device.value) return
  setDeviceAlias(device.value.device_id, draftAlias.value)
  toast.success('Имя устройства обновлено для веба')
}

function resetAlias() {
  if (!device.value) return
  draftAlias.value = ''
  setDeviceAlias(device.value.device_id, '')
  toast.info('Пользовательское имя сброшено')
}

onMounted(loadDevice)
</script>

<style scoped>
.device-page {
  max-width: 1180px;
  margin: 24px auto;
  display: grid;
  gap: 18px;
}

.device-shell {
  border: 2px solid var(--tenant-accent);
}

.device-shell__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.device-shell__eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--tenant-accent);
  font-weight: 700;
  margin-bottom: 8px;
}

.device-shell__title {
  font-size: 30px;
  margin-bottom: 6px;
}

.device-shell__grid {
  margin-top: 18px;
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.device-layout {
  display: grid;
  gap: 18px;
  grid-template-columns: 1.1fr 0.9fr;
}

.info-box {
  padding: 16px;
  border-radius: 18px;
  background: #f8fbff;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.info-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}

.actions-grid,
.rename-actions {
  display: grid;
  gap: 12px;
}

.rename-actions {
  margin-top: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.warning-chip {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fdba74;
  font-weight: 600;
}

.mt-10 {
  margin-top: 10px;
}

@media (max-width: 900px) {
  .device-shell__grid,
  .device-layout,
  .rename-actions {
    grid-template-columns: 1fr;
  }
}
</style>
