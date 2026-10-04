<script setup>
import { computed, ref } from 'vue'
import { geoMercator, geoPath } from 'd3-geo'
import { useElection } from '../stores/election'
import { fmtInt, fmtPct, fmtProb } from '../utils/fmt'
import geoRN from '../assets/geo_RN.json'

const s = useElection()
const W = 760, H = 460

const items = computed(() => s.mapData?.items || [])
const cands = computed(() => s.mapData?.cands || {})
const byId = computed(() => new Map(items.value.map((i) => [i.m, i])))
const nameOf = (id) => cands.value[id]?.n || ''
const winnerOf = (i) => (s.mode === 'projecao' ? (i.pj || i.w) : i.w)

// Malha GeoJSON do RN 100% normalizada (167 municípios, anti-horário garantido)
const geoData = geoRN

// Projeção Mercator perfeitamente ajustada aos 167 municípios
const projection = computed(() => {
  return geoMercator().fitExtent([[16, 16], [W - 16, H - 16]], geoData)
})

const pathGen = computed(() => (projection.value ? geoPath(projection.value) : null))

const shapes = computed(() => {
  if (!pathGen.value) return []
  return geoData.features.map((f) => ({
    id: String(f.properties.codarea ?? f.properties.id),
    d: pathGen.value(f),
  }))
})

const selId = computed(() => (s.isMun ? s.scope.slice(4) : null))
const ordered = computed(() => {
  const a = shapes.value
  return selId.value ? [...a.filter((p) => p.id !== selId.value), ...a.filter((p) => p.id === selId.value)] : a
})

// Principais cidades distribuídas pelas regiões do RN
const landmarkCities = [
  { id: '2408102', name: 'Natal' },
  { id: '2408003', name: 'Mossoró' },
  { id: '2402006', name: 'Caicó' },
  { id: '2409407', name: 'Pau dos Ferros' },
  { id: '2407203', name: 'Macau' },
]

const landmarks = computed(() => {
  if (!pathGen.value) return []
  const byCode = new Map(geoData.features.map((f) => [String(f.properties.codarea), f]))
  const res = []
  for (const c of landmarkCities) {
    const feat = byCode.get(c.id)
    if (feat) {
      const [x, y] = pathGen.value.centroid(feat)
      if (x && y) res.push({ ...c, x: Math.round(x), y: Math.round(y) })
    }
  }
  return res
})

function paint(id) {
  const i = byId.value.get(id)
  const w = i && winnerOf(i)
  if (!w) return { fill: '#e2e8f0', op: 1 }
  const op = s.mode === 'projecao' ? 0.45 + 0.55 * (i.pw ?? 0.7) : 0.4 + 0.6 * Math.min((i.f || 0) / 100, 1)
  return { fill: s.colorOf(w), op }
}

const counts = computed(() => {
  const m = {}
  for (const i of items.value) {
    const w = winnerOf(i)
    if (w) m[w] = (m[w] || 0) + 1
  }
  return Object.entries(m).sort((a, b) => b[1] - a[1])
})

const hoveredId = ref(null)
const hoverPos = ref({ x: 0, y: 0 })

const activeMun = computed(() => {
  const id = hoveredId.value || selId.value
  return id ? byId.value.get(id) : null
})

const hoverTag = computed(() => {
  if (!hoveredId.value) return null
  const i = byId.value.get(hoveredId.value)
  if (!i) return null
  const w = winnerOf(i)
  return {
    name: i.n,
    leader: w ? nameOf(w) : null,
    pct: w ? fmtPct(i.wp) : null,
    color: w ? s.colorOf(w) : null,
    x: hoverPos.value.x,
    y: hoverPos.value.y,
  }
})

function handleMouseMove(id, e) {
  hoveredId.value = id
  const stage = e.currentTarget.closest('.stage')
  if (stage) {
    const r = stage.getBoundingClientRect()
    hoverPos.value = {
      x: e.clientX - r.left,
      y: e.clientY - r.top,
    }
  }
}

function handleMouseLeave() {
  hoveredId.value = null
}

function toggleSelect(id) {
  if (selId.value === id) {
    s.selectScope(s.RN)
  } else {
    s.selectScope('mun:' + id)
  }
}
</script>

<template>
  <section class="map-panel">
    <header class="sec-head">
      <div>
        <h2>Mapa do Rio Grande do Norte</h2>
        <p class="sub">167 municípios · Liderança por apuração e projeção</p>
      </div>
      <div class="seg" role="group" aria-label="Critério de cor">
        <button :class="{ on: s.mode === 'atual' }" @click="s.mode = 'atual'">Apurado</button>
        <button :class="{ on: s.mode === 'projecao' }" @click="s.mode = 'projecao'">Projeção final</button>
      </div>
    </header>

    <!-- Placar resumido de prefeituras/municípios conquistados -->
    <div v-if="counts.length" class="leaders-strip">
      <div v-for="[id, n] in counts.slice(0, 5)" :key="id" class="chip">
        <i class="dot" :style="{ background: s.colorOf(id) }"></i>
        <b class="chip-name">{{ nameOf(id) }}</b>
        <span class="chip-count">{{ n }} {{ n === 1 ? 'mun.' : 'muns.' }}</span>
      </div>
    </div>

    <!-- Barra de inspeção interativa de município (não obstrui o mapa) -->
    <div class="active-city-bar">
      <template v-if="activeMun">
        <div class="ac-main">
          <div class="ac-left">
            <span class="ac-pin">📍</span>
            <b class="ac-name">{{ activeMun.n }}</b>
            <span class="ac-badge">{{ fmtPct(activeMun.f) }} apurado</span>
            <span class="ac-stat">Válidos: <b>{{ fmtInt(activeMun.v) }}</b></span>
            <span v-if="activeMun.e" class="ac-stat">Eleitorado: <b>{{ fmtInt(activeMun.e) }}</b></span>
          </div>
          <div v-if="activeMun.top && activeMun.top.length" class="ac-cands">
            <div v-for="(c, idx) in activeMun.top.slice(0, 2)" :key="c.id" class="ac-cand">
              <span class="ac-rank">{{ idx + 1 }}º</span>
              <i class="dot" :style="{ background: s.colorOf(c.id) }"></i>
              <span class="ac-cname">{{ c.n }}</span>
              <b class="ac-cpct">{{ fmtPct(c.pct) }}</b>
              <small class="ac-cvotes">({{ fmtInt(c.v) }})</small>
            </div>
            <div v-if="activeMun.wv && activeMun.sv" class="ac-diff">
              Vantagem: <b>{{ fmtInt(activeMun.wv - activeMun.sv) }}</b>
            </div>
          </div>
          <div v-else-if="winnerOf(activeMun)" class="ac-cands">
            <div class="ac-cand">
              <i class="dot" :style="{ background: s.colorOf(winnerOf(activeMun)) }"></i>
              <span class="ac-cname">{{ nameOf(winnerOf(activeMun)) }}</span>
              <b class="ac-cpct">{{ fmtPct(activeMun.wp) }}</b>
            </div>
          </div>
          <button v-if="selId !== activeMun.m" class="ac-btn" @click="toggleSelect(activeMun.m)">
            Ver boletim completo →
          </button>
          <button v-else class="ac-btn clear" @click="toggleSelect(activeMun.m)">
            ✕ Voltar ao RN
          </button>
        </div>
      </template>
      <div v-else class="ac-hint">
        <span>💡 Passe o mouse sobre qualquer cidade para ver os votos ou clique para filtrar o boletim.</span>
      </div>
    </div>

    <!-- Palco do mapa com visual limpo e sem caixas escuras obstrutivas -->
    <div class="stage" @pointerleave="handleMouseLeave">
      <svg :viewBox="`0 0 ${W} ${H}`" class="rn-svg" role="img" aria-label="Mapa do Rio Grande do Norte">
        <!-- Municípios -->
        <g class="muns-group">
          <path
            v-for="p in ordered"
            :key="p.id"
            :d="p.d"
            :fill="paint(p.id).fill"
            :fill-opacity="paint(p.id).op"
            :class="['mun', { sel: p.id === selId, hover: p.id === hoveredId }]"
            @click="toggleSelect(p.id)"
            @pointermove="handleMouseMove(p.id, $event)"
          />
        </g>

        <!-- Marcadores de cidades polo para referência geográfica -->
        <g class="landmarks-group">
          <g v-for="lm in landmarks" :key="lm.id" class="landmark" :transform="`translate(${lm.x}, ${lm.y})`">
            <circle r="3" class="lm-dot" />
            <text dx="5" dy="3.5" class="lm-text">{{ lm.name }}</text>
          </g>
        </g>
      </svg>

      <!-- Mini-tag suave e compacta que segue o cursor sem cobrir o mapa -->
      <div
        v-if="hoverTag"
        class="cursor-tag"
        :style="{ left: hoverTag.x + 'px', top: hoverTag.y + 'px' }"
      >
        <span class="ct-name">{{ hoverTag.name }}</span>
        <template v-if="hoverTag.leader">
          <i class="dot" :style="{ background: hoverTag.color }"></i>
          <span class="ct-leader">{{ hoverTag.leader }} ({{ hoverTag.pct }})</span>
        </template>
      </div>
    </div>

    <!-- Legenda de cores -->
    <ul class="legend">
      <li v-for="[id, n] in counts" :key="id">
        <i class="dot" :style="{ background: s.colorOf(id) }"></i>
        <b>{{ n }}</b> {{ nameOf(id) }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.map-panel {
  position: relative;
}

.sec-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}
.sub {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 13.5px;
}

.leaders-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  border: 1px solid var(--line);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
}
.chip-name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chip-count {
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
}

/* Barra interativa de município */
.active-city-bar {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 12px;
  min-height: 44px;
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}
.ac-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  flex-wrap: wrap;
}
.ac-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ac-pin {
  font-size: 14px;
}
.ac-name {
  font-size: 15px;
  color: var(--ink);
}
.ac-badge {
  background: #0f1b33;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 12px;
}
.ac-stat {
  font-size: 12.5px;
  color: #475569;
}
.ac-stat b {
  color: var(--ink);
}

.ac-cands {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.ac-cand {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
}
.ac-rank {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}
.ac-cname {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}
.ac-cpct {
  color: var(--ink);
}
.ac-cvotes {
  color: #64748b;
  font-size: 11px;
}
.ac-diff {
  font-size: 11.5px;
  color: #0f766e;
  background: #ccfbf1;
  padding: 2px 6px;
  border-radius: 4px;
}

.ac-btn {
  background: #fff;
  border: 1px solid #94a3b8;
  color: var(--ink);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: auto;
  transition: all 0.15s;
}
.ac-btn:hover {
  background: var(--ink);
  color: #fff;
  border-color: var(--ink);
}
.ac-btn.clear {
  background: #fee2e2;
  color: #991b1b;
  border-color: #fca5a5;
}

.ac-hint {
  color: #64748b;
  font-size: 13px;
}

/* Palco do mapa */
.stage {
  position: relative;
  width: 100%;
  border-radius: 6px;
  user-select: none;
}
.rn-svg {
  width: 100%;
  height: auto;
  display: block;
}

.mun {
  stroke: #94a3b8;
  stroke-width: 0.7;
  cursor: pointer;
  transition: fill 0.25s, fill-opacity 0.25s, stroke 0.15s;
}
.mun:hover, .mun.hover {
  stroke: #0f1b33;
  stroke-width: 2;
  fill-opacity: 0.95 !important;
}
.mun.sel {
  stroke: #000;
  stroke-width: 2.6;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,0.35));
}

.landmarks-group {
  pointer-events: none;
}
.lm-dot {
  fill: #0f1b33;
  stroke: #fff;
  stroke-width: 1.2;
}
.lm-text {
  font-size: 11px;
  font-weight: 700;
  fill: #0f1b33;
  paint-order: stroke;
  stroke: #fff;
  stroke-width: 2.8;
  stroke-linejoin: round;
}

/* Mini tag discreta que segue o cursor */
.cursor-tag {
  position: absolute;
  pointer-events: none;
  transform: translate(14px, -28px);
  background: rgba(15, 27, 51, 0.92);
  color: #fff;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(4px);
  z-index: 30;
}
.ct-name {
  font-weight: 700;
}
.ct-leader {
  color: #e2e8f0;
  font-size: 11.5px;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding: 0;
  margin: 10px 0 0;
  font-size: 13.5px;
}
.legend b {
  font-family: var(--display);
  font-size: 16px;
}
</style>
