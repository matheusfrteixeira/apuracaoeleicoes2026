<script setup>
import { computed } from 'vue'
import { useElection } from '../stores/election'
import { fmtPct, fmtProb, fmtInt } from '../utils/fmt'
import TimelineChart from './TimelineChart.vue'

const s = useElection()
const n = computed(() => s.national)
const fc = computed(() => n.value?.forecast)
const projOf = computed(() => Object.fromEntries((fc.value?.proj || []).map((p) => [p.id, p])))
const rows = computed(() => (n.value?.cand || []).slice(0, 5))
const scale = computed(() => Math.max(...rows.value.map((c) => Math.max(c.pct, projOf.value[c.id]?.hi || 0)), 1) * 1.05)
const byId = computed(() => Object.fromEntries((n.value?.cand || []).map((c) => [c.id, c])))
const nameOf = (id) => byId.value[id]?.nome || id

// Mapa em grade (cartograma) das 27 UFs: [coluna, linha]
const GRID = { RR: [2, 0], AP: [3, 0], AM: [1, 1], PA: [2, 1], MA: [3, 1], CE: [4, 1], RN: [5, 1], AC: [0, 2], RO: [1, 2],
  TO: [2, 2], PI: [3, 2], PE: [4, 2], PB: [5, 2], MT: [1, 3], GO: [2, 3], BA: [3, 3], AL: [4, 3], MS: [1, 4], DF: [2, 4],
  MG: [3, 4], SE: [4, 4], SP: [2, 5], RJ: [3, 5], ES: [4, 5], PR: [2, 6], SC: [3, 6], RS: [2, 7] }
const tiles = computed(() => (n.value?.by_uf || []).filter((u) => GRID[u.uf]).map((u) => {
  const c = u.w ? s.colorOf(u.w) : '#2b3a5c'
  const p = 35 + 65 * Math.min(u.f / 100, 1)
  return { ...u, col: GRID[u.uf][0] + 1, row: GRID[u.uf][1] + 1, bg: `color-mix(in srgb, ${c} ${p}%, #16233f)`,
    tip: `${u.nome}: ${nameOf(u.w)} ${fmtPct(u.wp)} · ${fmtPct(u.f)} apurado` }
}))
</script>

<template>
  <section class="nat" v-if="n">
    <div class="id">
      <span class="small">Brasil · Presidente</span>
      <div class="big">{{ fmtPct(n.apuracao.pct) }}</div>
      <span class="small">das seções apuradas · {{ fmtInt(n.votos.validos) }} votos válidos</span>
      <p class="verdict" v-if="fc?.proj?.length">
        Projeção: <b>{{ nameOf(fc.lider) }}</b> lidera com {{ fmtPct(fc.proj[0].pct) }}.
        <template v-if="fc.p2t != null && fc.p2t > 0.005">Chance de <b>segundo turno: {{ fmtProb(fc.p2t) }}</b>.</template>
        <template v-else>Chance de vitória no 1º turno.</template>
      </p>
    </div>

    <ol class="race">
      <li v-for="c in rows" :key="c.id">
        <div class="who"><b>{{ c.nome }}</b><small>{{ c.partido }}</small></div>
        <div class="track">
          <i class="ghost" :style="{ width: (projOf[c.id]?.pct || 0) / scale * 100 + '%', background: s.colorOf(c.id) }"></i>
          <i class="bar" :style="{ width: c.pct / scale * 100 + '%', background: s.colorOf(c.id) }"></i>
        </div>
        <div class="num"><b>{{ fmtPct(c.pct) }}</b><small v-if="projOf[c.id]">proj. {{ fmtPct(projOf[c.id].pct) }}</small></div>
      </li>
    </ol>

    <div class="chart">
      <span class="small">Projeção do Brasil conforme a apuração avança</span>
      <TimelineChart :points="s.histNational" :color-of="s.colorOf" :name-of="nameOf" dark compact :height="150" />
    </div>

    <div class="ufs" aria-label="Candidato à frente em cada estado">
      <div v-for="t in tiles" :key="t.uf" class="tile" :class="{ me: t.uf === s.meta?.uf }" :title="t.tip"
           :style="{ gridColumn: t.col, gridRow: t.row, background: t.bg }">{{ t.uf }}</div>
    </div>
  </section>
  <section class="nat loading" v-else><span class="small">Aguardando os primeiros dados do Brasil…</span></section>
</template>

<style scoped>
.nat { display: grid; grid-template-columns: minmax(220px, 1fr) minmax(300px, 1.6fr) minmax(240px, 1.2fr) 200px; gap: 28px;
  padding: 10px 28px 22px; align-items: start; }
.small { color: #9fb0d0; font-size: 13px; }
.big { font: 700 64px/1 var(--display); letter-spacing: -.01em; margin: 2px 0; }
.verdict { margin: 10px 0 0; font-size: 15px; line-height: 1.4; color: #dce4f5; max-width: 34ch; }
.race { list-style: none; margin: 0; padding: 0; display: grid; gap: 9px; }
.race li { display: grid; grid-template-columns: 130px 1fr 78px; gap: 10px; align-items: center; }
.who b { display: block; font-weight: 600; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.who small, .num small { color: #8f9dbb; font-size: 12px; }
.track { position: relative; height: 16px; background: rgba(255,255,255,.07); border-radius: 2px; }
.track i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 2px; transition: width .6s ease; }
.ghost { opacity: .32; } .bar { height: 60%; top: 20%; }
.num { text-align: right; line-height: 1.1; } .num b { font: 600 20px var(--display); display: block; }
.ufs { display: grid; grid-template-columns: repeat(6, 28px); grid-auto-rows: 28px; gap: 3px; justify-content: end; }
.tile { display: grid; place-items: center; font: 600 11px var(--body); border-radius: 3px; color: #fff; cursor: default; transition: background .6s; }
.tile.me { outline: 2px solid #fff; outline-offset: 1px; }
.loading { padding: 24px 28px; }
@media (max-width: 1180px) { .nat { grid-template-columns: 1fr 1fr; } .ufs { justify-content: start; } }
@media (max-width: 640px) { .nat { grid-template-columns: 1fr; padding: 8px 16px 20px; } .big { font-size: 52px; } .race li { grid-template-columns: 100px 1fr 70px; } }
</style>
