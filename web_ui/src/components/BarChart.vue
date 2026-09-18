<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  labels: string[]
  series: Array<{ name: string; data: number[]; color?: string }>
  percent?: boolean
  horizontal?: boolean
}>()
const root = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined

function render() {
  if (!root.value) return
  chart ||= echarts.init(root.value)
  const category = { type: 'category' as const, data: props.labels, axisLabel: { color: '#64748b', interval: 0 } }
  const value = {
    type: 'value' as const,
    max: props.percent ? 1 : undefined,
    axisLabel: { color: '#64748b', formatter: props.percent ? (v: number) => `${Math.round(v * 100)}%` : undefined },
    splitLine: { lineStyle: { color: '#e8edf3' } },
  }
  chart.setOption({
    animationDuration: 500,
    color: props.series.flatMap((item) => item.color ? [item.color] : []),
    tooltip: { trigger: 'axis', valueFormatter: props.percent ? (v: unknown) => `${(Number(v) * 100).toFixed(1)}%` : undefined },
    legend: { top: 0, textStyle: { color: '#475569' } },
    grid: { left: props.horizontal ? 150 : 48, right: 24, top: 44, bottom: 48 },
    xAxis: props.horizontal ? value : category,
    yAxis: props.horizontal ? category : value,
    series: props.series.map((item) => ({ ...item, type: 'bar', barMaxWidth: 34, itemStyle: { borderRadius: [4, 4, 0, 0] } })),
  }, true)
}

const resize = () => chart?.resize()
onMounted(() => { render(); window.addEventListener('resize', resize) })
watch(() => [props.labels, props.series], render, { deep: true })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart?.dispose() })
</script>

<template><div ref="root" class="chart" role="img" aria-label="数据对比图表" /></template>
