<template>
  <div class="charts-page">
    <h1 class="page-title">Показания датчиков</h1>

    <div class="filters">
      <div class="filter">
        <label class="label">Источник</label>
        <select v-model="source" class="select">
          <option value="fake">fake</option>
          <option value="real">real</option>
        </select>
      </div>

      <div class="filter">
        <label class="label">Период</label>
        <select v-model="period" class="select">
          <option value="1h">1 час</option>
          <option value="6h">6 часов</option>
          <option value="24h">24 часа</option>
          <option value="7d">7 дней</option>
        </select>
      </div>

      <div class="filter">
        <label class="label">Точки</label>
        <input v-model.number="limit" type="number" min="10" max="5000" class="input" />
      </div>

      <div class="filter actions">
        <button class="btn" @click="reloadAll" :disabled="loading">
          {{ loading ? 'Загрузка…' : 'Обновить' }}
        </button>
      </div>
    </div>

    <div class="grid">
      <!-- LEFT: devices -->
      <section class="card">
        <div class="card-title">Устройства</div>

        <div class="devices-list" role="listbox" aria-label="Devices">
          <button
            v-for="d in devices"
            :key="d.id"
            type="button"
            class="device-row"
            :class="{ selected: d.id === selectedDeviceId }"
            @click="selectDevice(d.id)"
          >
            <div class="device-name">{{ d.name }}</div>
            <div class="device-sub">{{ d.id }}</div>
          </button>

          <div v-if="!devices.length && !loading" class="muted">Нет устройств</div>
        </div>
      </section>

      <!-- MIDDLE: sensors -->
      <section class="card">
        <div class="card-title">Датчики</div>

        <div class="sensors-box">
          <div class="sensors-scroll">
            <label v-for="s in sensors" :key="s.key" class="sensor-row">
              <input type="checkbox" v-model="selectedSensors" :value="s.key" />
              <span>{{ s.label }}</span>
            </label>
          </div>
        </div>

        <div class="hint">
          Выбрано: {{ selectedSensors.length }}
        </div>
      </section>


      <section class="card charts-card">
        <div class="card-title">Графики</div>

        <div v-if="error" class="error">{{ error }}</div>
        <div v-else-if="!selectedDeviceId" class="muted">Выбери устройство слева</div>

        <div v-else class="charts-area">
          <div v-for="s in selectedSensors" :key="s" class="chart-panel">
            <div class="chart-panel-title">{{ sensorLabel(s) }}</div>

            <div class="chart-box">
              <canvas :ref="el => setCanvasRef(s, el)"></canvas>
            </div>

            <div v-if="series[s]?.length === 0" class="muted small">
              Нет данных
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { nextTick } from "vue";

import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  CategoryScale,
  Tooltip,
  Legend
} from "chart.js";

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

export default {
  name: "ChartsView",

  data() {
    return {
      loading: false,
      error: "",

      source: "fake",
      period: "24h",
      limit: 200,

      devices: [],
      selectedDeviceId: "",

      sensors: [
        { key: "temperature", label: "Температура" },
        { key: "humidity", label: "Влажность" },
        { key: "pressure", label: "Давление" }
      ],
      selectedSensors: ["temperature"],

      series: {},         
      canvasByKey: new Map(),
      chartByKey: new Map()
    };
  },

  mounted() {
    this.reloadAll();
    window.addEventListener("resize", this.resizeAllCharts);
  },

  beforeUnmount() {
    window.removeEventListener("resize", this.resizeAllCharts);
    this.destroyAllCharts();
  },

  watch: {
    source() { this.reloadAll(); },
    period() { this.reloadSeries(); },
    limit() { this.reloadSeries(); },
    selectedDeviceId() { this.reloadSeries(); },
    selectedSensors() {
      // при смене набора сенсоров пересобираем графики
      this.$nextTick(() => this.renderAllCharts());
    }
  },

  methods: {
    sensorLabel(key) {
      const s = this.sensors.find(x => x.key === key);
      return s ? s.label : key;
    },

    setCanvasRef(key, el) {
      if (!el) return;
      this.canvasByKey.set(key, el);
    },

    selectDevice(id) {
      this.selectedDeviceId = id;
    },

    async reloadAll() {
      this.error = "";
      this.loading = true;
      try {
        await this.loadDevices();
        if (this.devices.length && !this.selectedDeviceId) {
          this.selectedDeviceId = this.devices[0].id;
        }
        await this.reloadSeries();
      } catch (e) {
        this.error = String(e?.message || e);
      } finally {
        this.loading = false;
      }
    },

    async reloadSeries() {
      this.error = "";
      if (!this.selectedDeviceId) return;

      this.loading = true;
      try {
        const data = await this.apiFetchSeries({
          source: this.source,
          period: this.period,
          limit: this.limit,
          deviceId: this.selectedDeviceId,
          sensors: this.selectedSensors
        });

        this.series = data || {};

        await nextTick();       
        this.renderAllCharts(); 
      } catch (e) {
        this.error = String(e?.message || e);
      } finally {
        this.loading = false;
      }
    },

    async loadDevices() {
      const devices = await this.apiFetchDevices({ source: this.source });
      // ожидаем: [{id, name}, ...]
      this.devices = devices || [];
    },

    // ---- Chart rendering ----

    destroyAllCharts() {
      for (const ch of this.chartByKey.values()) {
        try { ch.destroy(); } catch {}
      }
      this.chartByKey.clear();
    },

    renderAllCharts() {
      for (const [k, ch] of this.chartByKey.entries()) {
        if (!this.selectedSensors.includes(k)) {
          try { ch.destroy(); } catch {}
          this.chartByKey.delete(k);
        }
      }

      for (const sensorKey of this.selectedSensors) {
        this.renderChart(sensorKey);
      }
    },

    resizeAllCharts() {
      for (const ch of this.chartByKey.values()) {
        try { ch.resize(); } catch {}
      }
    },

    renderChart(sensorKey) {
      const canvas = this.canvasByKey.get(sensorKey);
      if (!canvas) return;

      const points = this.series[sensorKey] || [];

      const labels = points.map(p => String(p.t));
      const values = points.map(p => Number(p.v));

      const existing = this.chartByKey.get(sensorKey);
      if (existing) {
        existing.data.labels = labels;
        existing.data.datasets[0].data = values;
        existing.update();
        return;
      }

      const ctx = canvas.getContext("2d");
      const chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: this.sensorLabel(sensorKey),
              data: values,
              tension: 0.2,
              pointRadius: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false, 
          plugins: {
            legend: { display: false },
            tooltip: { enabled: true }
          },
          scales: {
            x: { display: true },
            y: { display: true }
          }
        }
      });

      this.chartByKey.set(sensorKey, chart);
    },

    async apiFetchDevices({ source }) {
      return [
        { id: "dev-0001", name: "dev-0001" },
        { id: "dev-0002", name: "dev-0002" },
        { id: "dev-0003", name: "dev-0003" }
      ];
    },

    async apiFetchSeries({ deviceId, sensors }) {
      const now = Date.now();
      const make = () =>
        Array.from({ length: 80 }, (_, i) => ({
          t: new Date(now - (79 - i) * 60_000).toISOString(),
          v: Math.sin(i / 8) * 10 + 20 + (Math.random() - 0.5)
        }));

      const out = {};
      for (const s of sensors) out[s] = make();
      return out;
    }
  }
};
</script>

<style scoped src="../assets/charts.css"></style>
