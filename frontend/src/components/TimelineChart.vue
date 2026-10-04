<script setup>
// Evolução da PROJEÇÃO final conforme a apuração avança (eixo X = % de seções apuradas).
// Linha cheia = projeção; tracejada = apurado até agora. A projeção "assenta" quando a apuração avança.
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  points: { type: Array, default: () => [] },
  colorOf: { type: Function, required: true },
  nameOf: { type: Function, required: true },
  dark: Boolean,
  height: { type: Number, default: 260 },
  compact: Boolean,
})
const el = ref(null)
let chart, ro

function render() {
  if (!chart) return
  const pts = props.points.filter((p) => p.f >= 1)  // <1% apurado = só ruído
  const last = pts[pts.length - 1]
  const ids = last ? Object.keys(last.p).slice(0, props.compact ? 4 : 5) : []
  const txt = props.dark ? '#a9b6d0' : '#5b6880'
  const grid = props.dark ? 'rgba(255,255,255,.08)' : '#e3e7ee'
  const series = []
  for (const id of ids) {
    const col = props.colorOf(id)
    series.push({
      name: props.nameOf(id), type: 'line', showSymbol: false, smooth: false, z: 3,
      lineStyle: { width: 2.5, color: col }, itemStyle: { color: col },
      data: pts.map((p) => [p.f, p.p[id]]),
    })
    if (!props.compact) {
      series.push({
        name: props.nameOf(id) + ' (apurado)', type: 'line', showSymbol: false, z: 2,
        lineStyle: { width: 1.2, color: col, type: 'dashed', opacity: 0.55 }, itemStyle: { color: col },
        data: pts.map((p) => [p.f, p.c[id]]),
      })
    }
  }
  chart.setOption({
    animation: false,
    grid: { left: 38, right: 10, top: 10, bottom: props.compact ? 18 : 38 },
    tooltip: {
      trigger: 'axis', confine: true,
      valueFormatter: (v) => (v == null ? '–' : v.toFixed(1).replace('.', ',') + '%'),
    },
    xAxis: {
      type: 'value', min: 0, max: 100, axisLabel: { color: txt, formatter: '{value}%', fontSize: 11 },
      splitLine: { show: false }, axisLine: { lineStyle: { color: grid } },
      name: props.compact ? '' : 'seções apuradas', nameLocation: 'middle', nameGap: 20, nameTextStyle: { color: txt, fontSize: 11 },
    },
    yAxis: {
      type: 'value', scale: true, axisLabel: { color: txt, formatter: '{value}%', fontSize: 11 },
      splitLine: { lineStyle: { color: grid } },
    },
    series,
  }, true)
}

onMounted(() => {
  chart = echarts.init(el.value, null, { renderer: 'canvas' })
  ro = new ResizeObserver(() => chart.resize())
  ro.observe(el.value)
  render()
})
onBeforeUnmount(() => { ro?.disconnect(); chart?.dispose() })
watch(() => [props.points, props.dark], render)
</script>

<template>
  <div ref="el" :style="{ height: height + 'px', width: '100%' }" role="img"
       aria-label="Evolução da projeção do percentual de votos por candidato"></div>
</template>
