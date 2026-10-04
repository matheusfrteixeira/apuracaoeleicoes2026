import { defineStore } from 'pinia'
import { ref, shallowRef, computed } from 'vue'
import { connect } from '../services/socket'

// Paleta distinguível (inclui daltonismo leve). Cores são atribuídas 1x por candidato e ficam estáveis.
export const PALETTE = ['#2457d6', '#e4572e', '#12a37f', '#f0a202', '#8e44c7', '#1597bb',
  '#d63f7b', '#6b7c93', '#6a8d1f', '#a3562a', '#3b3b98', '#c0392b']
const NEUTRAL = '#cfd5de'
const RN = 'uf:RN'

export const useElection = defineStore('election', () => {
  const connected = ref(false)
  const meta = shallowRef(null)
  const cargo = ref('1')
  const scope = ref(RN)
  const mapData = shallowRef(null)
  const result = shallowRef(null)
  const national = shallowRef(null)
  const histState = shallowRef([])
  const histNational = shallowRef([])
  const geo = shallowRef(null)
  const geoError = ref(false)
  const updatedAt = ref(0)
  const mode = ref('atual') // 'atual' | 'projecao' (como o mapa é colorido)

  // ---- cores estáveis por candidato
  const colors = new Map()
  const counters = {}
  const colorVersion = ref(0)
  function register(group, ids) {
    let added = false
    for (const id of [...ids].sort()) {
      if (colors.has(id)) continue
      const n = (counters[group] = (counters[group] || 0) + 1) - 1
      colors.set(id, PALETTE[n % PALETTE.length])
      added = true
    }
    if (added) colorVersion.value++
  }
  const colorOf = (id) => { colorVersion.value; return colors.get(id) || NEUTRAL }

  // ---- WebSocket
  let sock
  const sendSub = () => sock?.send({ op: 'sub', cargo: cargo.value, scope: scope.value })

  function onMessage(m) {
    updatedAt.value = Date.now()
    switch (m.t) {
      case 'meta': meta.value = m.data; break
      case 'national':
        register('1', m.data.cand.map((c) => c.id))
        national.value = m.data
        break
      case 'map':
        if (m.cargo !== cargo.value) break
        register(m.cargo, m.data.legend)
        mapData.value = m.data
        break
      case 'result':
        if (m.cargo === cargo.value && m.scope === scope.value) {
          register(m.cargo, m.data.cand.map((c) => c.id))
          result.value = m.data
        }
        break
      case 'hist':
        if (m.scope === 'br') histNational.value = m.data
        else if (m.cargo === cargo.value) histState.value = m.data
        break
      case 'hist_point':
        if (m.scope === 'br') histNational.value = [...histNational.value, m.point]
        else if (m.cargo === cargo.value) histState.value = [...histState.value, m.point]
        break
    }
  }

  async function init() {
    sock = connect({
      onOpen: () => { connected.value = true; sendSub() },
      onClose: () => { connected.value = false },
      onMessage,
    })
    try {
      const r = await fetch('/api/geo')
      if (!r.ok) throw new Error(r.status)
      geo.value = await r.json()
    } catch { geoError.value = true }
  }

  function selectCargo(c) {
    if (c === cargo.value) return
    cargo.value = c
    scope.value = RN
    mapData.value = result.value = null
    histState.value = []
    sendSub()
  }
  function selectScope(s) {
    if (s === scope.value) return
    scope.value = s
    result.value = null
    sendSub()
  }

  const cargoMeta = computed(() => meta.value?.cargos.find((c) => c.code === cargo.value))
  const isMun = computed(() => scope.value.startsWith('mun:'))

  return {
    connected, meta, cargo, scope, mapData, result, national, histState, histNational, geo, geoError,
    updatedAt, mode, cargoMeta, isMun, colorOf, init, selectCargo, selectScope, RN,
  }
})
