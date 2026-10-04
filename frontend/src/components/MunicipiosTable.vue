<script setup>
import { computed, ref } from 'vue'
import { useElection } from '../stores/election'
import { fmtInt, fmtPct, fmtProb } from '../utils/fmt'

const s = useElection()
const q = ref('')
const who = ref('')
const sort = ref('n')

const items = computed(() => s.mapData?.items || [])
const cands = computed(() => s.mapData?.cands || {})
const winnerOf = (i) => (s.mode === 'projecao' ? i.pj : i.w)
const nm = (id) => cands.value[id]?.n || ''
const clean = (t) => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
const margin = (i) => i.wp - i.sp

const leaders = computed(() => {
  const m = {}
  for (const i of items.value) { const w = winnerOf(i); if (w) m[w] = (m[w] || 0) + 1 }
  return Object.entries(m).sort((a, b) => b[1] - a[1])
})

const SORTS = {
  n: (a, b) => a.n.localeCompare(b.n, 'pt-BR'),
  fd: (a, b) => b.f - a.f,
  fa: (a, b) => a.f - b.f,
  md: (a, b) => margin(b) - margin(a),
  ma: (a, b) => margin(a) - margin(b),
  e: (a, b) => b.e - a.e,
}
const rows = computed(() => {
  const t = clean(q.value)
  return items.value
    .filter((i) => (!t || clean(i.n).includes(t)) && (!who.value || winnerOf(i) === who.value))
    .sort(SORTS[sort.value])
})
</script>

<template>
  <section class="tbl">
    <header class="sec-head">
      <h2>Municípios <small>{{ rows.length }} de {{ items.length }}</small></h2>
    </header>
    <div class="filters">
      <input v-model="q" type="search" placeholder="Buscar município" aria-label="Buscar município" />
      <select v-model="who" aria-label="Filtrar por candidato à frente">
        <option value="">Todos os candidatos</option>
        <option v-for="[id, n] in leaders" :key="id" :value="id">{{ nm(id) }} ({{ n }})</option>
      </select>
      <select v-model="sort" aria-label="Ordenar">
        <option value="n">Ordem alfabética</option>
        <option value="fd">Mais apurados</option>
        <option value="fa">Menos apurados</option>
        <option value="ma">Disputa mais apertada</option>
        <option value="md">Maior vantagem</option>
        <option value="e">Maior eleitorado</option>
      </select>
    </div>

    <div class="scroll">
      <table>
        <thead><tr><th>Município</th><th>À frente</th><th class="r">%</th><th class="r">Vantagem</th><th>Apurado</th><th class="r">Chance</th></tr></thead>
        <tbody>
          <tr v-for="i in rows" :key="i.m" :class="{ sel: s.scope === 'mun:' + i.m }" @click="s.selectScope('mun:' + i.m)">
            <td>{{ i.n }}<small>{{ fmtInt(i.e) }} eleitores</small></td>
            <td>
              <template v-if="winnerOf(i)"><i class="dot" :style="{ background: s.colorOf(winnerOf(i)) }"></i>{{ nm(winnerOf(i)) }}</template>
              <span v-else class="mut">–</span>
              <small v-if="s.mode === 'atual' && i.pj && i.w && i.pj !== i.w" class="flip">projeção vira para {{ nm(i.pj) }}</small>
            </td>
            <td class="r">{{ i.w ? fmtPct(s.mode === 'atual' ? i.wp : i.pjp) : '–' }}</td>
            <td class="r">{{ i.s ? fmtPct(margin(i)).replace('%', ' pp') : '–' }}</td>
            <td><div class="mini"><i :style="{ width: i.f + '%' }"></i></div><small>{{ fmtPct(i.f, 0) }}</small></td>
            <td class="r">{{ fmtProb(i.pw) }}</td>
          </tr>
          <tr v-if="!rows.length"><td colspan="6" class="mut pad">Nenhum município encontrado com esses filtros.</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
h2 small { font: 400 14px var(--body); color: var(--muted); margin-left: 8px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.filters input, .filters select { font: 400 14px var(--body); padding: 7px 9px; border: 1px solid var(--line); border-radius: 2px; background: #fff; color: var(--text); min-width: 0; }
.filters input { flex: 1 1 160px; }
.scroll { max-height: 440px; overflow: auto; border-top: 1px solid var(--line); }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { position: sticky; top: 0; background: #fff; text-align: left; font-weight: 600; color: var(--muted); font-size: 12.5px; padding: 8px 6px; border-bottom: 1px solid var(--line); }
td { padding: 7px 6px; border-bottom: 1px solid #edf0f4; vertical-align: top; }
td small { display: block; color: var(--muted); font-size: 12px; }
.r { text-align: right; } .mut { color: var(--muted); } .pad { padding: 18px; text-align: center; }
tbody tr { cursor: pointer; } tbody tr:hover { background: #f4f6fa; } tr.sel { background: #e8eefc; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; }
.mini { height: 5px; background: #e3e7ee; min-width: 70px; margin-top: 7px; } .mini i { display: block; height: 100%; background: var(--ink); }
.flip { color: #b45309 !important; }
</style>
