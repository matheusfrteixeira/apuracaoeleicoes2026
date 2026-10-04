<script setup>
import { computed } from 'vue'
import { useElection } from '../stores/election'
import { fmtInt, fmtPct, fmtProb } from '../utils/fmt'

const s = useElection()
const r = computed(() => s.result)
const meta = computed(() => s.cargoMeta)
const fc = computed(() => r.value?.forecast)
const prop = computed(() => meta.value?.tipo === 'proporcional')
const projOf = computed(() => Object.fromEntries((fc.value?.proj || []).map((p) => [p.id, p])))
const nRows = computed(() => (prop.value ? Math.min(meta.value.vagas + 6, 24) : 8))
const rows = computed(() => (r.value?.cand || []).slice(0, nRows.value))
const scale = computed(() => Math.max(...rows.value.map((c) => Math.max(c.pct, projOf.value[c.id]?.hi || 0)), 1) * 1.04)
const nameOf = (id) => r.value?.cand.find((c) => c.id === id)?.nome || id

const turnout = computed(() => {
  const e = r.value?.eleitorado
  return e && e.comparecimento + e.abstencao ? (e.comparecimento / (e.comparecimento + e.abstencao)) * 100 : 0
})
const pctOfTotal = (n) => (r.value?.votos.total ? (n / r.value.votos.total) * 100 : 0)
const probs = computed(() =>
  Object.entries(fc.value?.prob || {}).filter(([, p]) => p > 0.004).sort((a, b) => b[1] - a[1]))
const stateLevel = computed(() => !s.isMun)
</script>

<template>
  <section class="race-panel" v-if="r">
    <header class="sec-head">
      <div>
        <h2>{{ r.nome }}</h2>
        <p class="sub">{{ meta?.nome }} · {{ fmtPct(r.apuracao.pct) }} das seções ({{ fmtInt(r.apuracao.apuradas) }} de {{ fmtInt(r.apuracao.total) }})</p>
      </div>
      <button v-if="s.isMun" class="back" @click="s.selectScope(s.RN)">← {{ s.meta?.uf_nome }}</button>
    </header>

    <div class="prog" aria-hidden="true"><i :style="{ width: r.apuracao.pct + '%' }"></i></div>
    <dl class="stats">
      <div><dt>Comparecimento</dt><dd>{{ fmtPct(turnout) }}</dd></div>
      <div><dt>Brancos</dt><dd>{{ fmtPct(pctOfTotal(r.votos.brancos)) }}</dd></div>
      <div><dt>Nulos</dt><dd>{{ fmtPct(pctOfTotal(r.votos.nulos)) }}</dd></div>
      <div><dt>Votos válidos</dt><dd>{{ fmtInt(r.votos.validos) }}</dd></div>
    </dl>

    <!-- Previsão -->
    <div class="verdict" v-if="fc?.proj?.length">
      <template v-if="probs.length">
        <p>
          Chance de terminar em 1º lugar<span v-if="s.isMun"> neste município</span>:
        </p>
        <div class="stack" role="img" :aria-label="'Probabilidades: ' + probs.map(([id, p]) => nameOf(id) + ' ' + fmtProb(p)).join(', ')">
          <span v-for="[id, p] in probs" :key="id" :style="{ flexGrow: p, background: s.colorOf(id) }">
            <template v-if="p > 0.14">{{ nameOf(id).split(' ')[0] }} {{ fmtProb(p) }}</template>
          </span>
        </div>
        <p v-if="stateLevel && fc.p2t != null && meta.vagas === 1" class="p2t">
          <template v-if="fc.p2t > 0.005">Probabilidade de <b>segundo turno: {{ fmtProb(fc.p2t) }}</b>
            (o líder projetado tem {{ fmtPct(fc.proj[0].pct) }} dos válidos).</template>
          <template v-else>O líder projetado ({{ fmtPct(fc.proj[0].pct) }}) deve vencer no <b>1º turno</b>.</template>
        </p>
      </template>
      <p v-else-if="meta?.code === '5'">Duas vagas em disputa: os dois mais votados são eleitos.</p>
      <p v-else-if="prop">Ranking por votos nominais. A divisão final das vagas depende do quociente partidário (ainda fora deste MVP).</p>
    </div>

    <TransitionGroup name="flip" tag="ol" class="race">
      <li v-for="(c, i) in rows" :key="c.id" :data-cut="prop && i === meta.vagas ? `abaixo da linha: fora das ${meta.vagas} vagas (pelos votos de agora)` : null"
          :class="{ cut: prop && i === meta.vagas }">
        <span class="rk">{{ i + 1 }}</span>
        <div class="who">
          <b>{{ c.nome }}</b>
          <small>{{ c.partido }} · {{ c.num }}<em v-if="c.eleito"> · eleito</em></small>
        </div>
        <div class="track">
          <i class="ghost" :style="{ width: (projOf[c.id]?.pct || 0) / scale * 100 + '%', background: s.colorOf(c.id) }"></i>
          <i class="bar" :style="{ width: c.pct / scale * 100 + '%', background: s.colorOf(c.id) }"></i>
          <i v-if="projOf[c.id] && projOf[c.id].hi > projOf[c.id].lo" class="whisker"
             :style="{ left: projOf[c.id].lo / scale * 100 + '%', width: (projOf[c.id].hi - projOf[c.id].lo) / scale * 100 + '%' }"></i>
        </div>
        <div class="num"><b>{{ fmtPct(c.pct) }}</b><small>{{ fmtInt(c.votos) }}</small></div>
      </li>
    </TransitionGroup>
    <p class="hint">Barra cheia: apurado. Barra clara: projeção do resultado final. Traço: intervalo de 95% da projeção.</p>
  </section>
  <section v-else class="race-panel"><p class="hint">Carregando {{ meta?.nome || 'cargo' }}…</p></section>
</template>

<style scoped>
.sub { margin: 2px 0 0; color: var(--muted); font-size: 14px; }
.back { border: 1px solid var(--line); background: #fff; padding: 6px 10px; font: 500 14px var(--body); cursor: pointer; border-radius: 2px; }
.back:hover { border-color: var(--ink); }
.prog { height: 4px; background: #e3e7ee; margin: 12px 0 10px; } .prog i { display: block; height: 100%; background: var(--ink); transition: width .6s; }
.stats { display: flex; gap: 22px; flex-wrap: wrap; margin: 0 0 14px; }
.stats div { display: grid; } .stats dt { color: var(--muted); font-size: 12.5px; } .stats dd { margin: 0; font: 600 20px var(--display); }
.verdict { border-left: 3px solid var(--ink); padding: 2px 0 2px 12px; margin: 0 0 14px; font-size: 14.5px; }
.verdict p { margin: 0 0 6px; }
.stack { display: flex; height: 26px; gap: 2px; margin-bottom: 8px; }
.stack span { display: grid; align-items: center; padding: 0 8px; color: #fff; font-size: 12.5px; font-weight: 600; white-space: nowrap; overflow: hidden; min-width: 3px; transition: flex-grow .6s; }
.p2t { margin-top: 2px !important; }
.race { list-style: none; margin: 0; padding: 0; position: relative; }
.race li { display: grid; grid-template-columns: 22px minmax(120px, 190px) 1fr 84px; gap: 10px; align-items: center; min-height: 46px; position: relative; }
.race li.cut { border-top: 2px dashed var(--ink); margin-top: 26px; }
.race li.cut::before { content: attr(data-cut); position: absolute; top: -21px; left: 0; font-size: 12px; color: var(--muted); }
.rk { font: 600 15px var(--display); color: var(--muted); text-align: right; }
.who b { display: block; font-weight: 600; font-size: 14.5px; line-height: 1.15; }
.who small { color: var(--muted); font-size: 12.5px; } .who em { font-style: normal; color: #0a7f5c; font-weight: 600; }
.track { position: relative; height: 20px; background: #eef1f5; }
.track i { position: absolute; left: 0; transition: width .6s ease, left .6s ease; }
.ghost { top: 0; bottom: 0; opacity: .3; } .bar { top: 4px; bottom: 4px; }
.whisker { top: 9px; height: 2px; background: var(--ink); opacity: .7; }
.num { text-align: right; line-height: 1.1; } .num b { font: 600 21px var(--display); display: block; } .num small { color: var(--muted); font-size: 12px; }
.flip-move { transition: transform .55s cubic-bezier(.2, .8, .2, 1); }
.hint { color: var(--muted); font-size: 13px; margin: 12px 0 0; }
@media (max-width: 560px) { .race li { grid-template-columns: 18px 1fr 70px; } .track { grid-column: 2 / 4; grid-row: 2; } }
@media (prefers-reduced-motion: reduce) { .flip-move, .track i { transition: none } }
</style>
