<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useElection } from '../stores/election'
import { ago } from '../utils/fmt'

const s = useElection()
const tick = ref(0)
let t
onMounted(() => (t = setInterval(() => tick.value++, 1000)))
onBeforeUnmount(() => clearInterval(t))
const updated = computed(() => { tick.value; return s.updatedAt ? ago(s.updatedAt) : '–' })
const sim = computed(() => (s.meta?.mode === 'mock' ? 'dados simulados (mock)' : 'base de ensaio do TSE'))
</script>

<template>
  <header class="top">
    <div class="brand">
      <h1>Apuração 2026</h1>
      <span class="live" :class="{ off: !s.connected }">
        <i></i>{{ s.connected ? 'ao vivo' : 'reconectando…' }}
      </span>
      <span class="muted">atualizado {{ updated }} · {{ sim }}</span>
    </div>
    <nav class="tabs" aria-label="Cargos">
      <button v-for="c in s.meta?.cargos" :key="c.code" :class="{ on: c.code === s.cargo }"
              @click="s.selectCargo(c.code)">{{ c.nome }}</button>
    </nav>
  </header>
</template>

<style scoped>
.top { display: flex; flex-wrap: wrap; gap: 14px 28px; align-items: center; justify-content: space-between; padding: 14px 28px; }
.brand { display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
h1 { font: 700 30px/1 var(--display); margin: 0; letter-spacing: .01em; }
.live { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; font-size: 14px; color: #ff6b6b; }
.live i { width: 9px; height: 9px; border-radius: 50%; background: currentColor; animation: pulse 1.6s infinite; }
.live.off { color: #f0a202; } .live.off i { animation: none; }
.muted { color: #8f9dbb; font-size: 13px; }
.tabs { display: flex; gap: 4px; flex-wrap: wrap; }
.tabs button { background: transparent; color: #c8d2e8; border: 0; border-bottom: 3px solid transparent; padding: 8px 12px 6px;
  font: 600 18px var(--display); cursor: pointer; }
.tabs button:hover { color: #fff; }
.tabs button.on { color: #fff; border-bottom-color: #ff6b6b; }
@keyframes pulse { 50% { opacity: .35 } }
@media (prefers-reduced-motion: reduce) { .live i { animation: none } }
</style>
