<script setup>
import { computed, onMounted } from 'vue'
import { useElection } from './stores/election'
import AppHeader from './components/AppHeader.vue'
import NationalStrip from './components/NationalStrip.vue'
import RnMap from './components/RnMap.vue'
import RacePanel from './components/RacePanel.vue'
import TimelineChart from './components/TimelineChart.vue'
import MunicipiosTable from './components/MunicipiosTable.vue'

const s = useElection()
onMounted(() => s.init())
const nameOf = (id) => s.mapData?.cands?.[id]?.n || id
const title = computed(() => `${s.cargoMeta?.nome || ''} · ${s.meta?.uf_nome || ''}`)
</script>

<template>
  <div class="band"><AppHeader /><NationalStrip /></div>
  <main class="board">
    <RnMap class="a-map" />
    <RacePanel class="a-race" />
    <section class="a-time">
      <header class="sec-head"><h2>Como a projeção evolui <small>{{ title }}</small></h2></header>
      <TimelineChart :points="s.histState" :color-of="s.colorOf" :name-of="nameOf" :height="300" />
      <p class="hint">Linha cheia: projeção do resultado final. Tracejada: percentual apurado até o momento. Conforme as seções entram, as duas se encontram.</p>
    </section>
    <MunicipiosTable class="a-table" />
  </main>
  <footer>MVP de apuração · projeção = votos apurados ÷ seções apuradas, com erro sistemático da ordem de apuração. Não é resultado oficial.</footer>
</template>
