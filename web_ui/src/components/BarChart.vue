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
  showValues?: boolean
  compact?: boolean
  wideLabels?: boolean
}>()
const root = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined
let resizeObserver: ResizeObserver | undefined

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
    grid: { left: props.horizontal ? (props.wideLabels ? 235 : 150) : 48, right: props.showValues ? 58 : 24, top: 44, bottom: props.compact ? 24 : 48 },
    xAxis: props.horizontal ? value : category,
    yAxis: props.horizontal ? category : value,
    series: props.series.map((item) => ({
      ...item,
      type: 'bar',
      barMaxWidth: props.compact ? 22 : 34,
      itemStyle: { borderRadius: props.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
      label: props.showValues ? {
        show: true,
        position: 'right',
        color: '#475569',
        fontSize: 11,
        formatter: props.percent ? ({ value }: { value: number }) => `${(Number(value) * 100).toFixed(1)}%` : undefined,
      } : undefined,
    })),
  }, true)
}

const resize = () => chart?.resize()
onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(([entry]) => {
    if (entry.contentRect.width > 0) chart?.resize()
  })
  if (root.value) resizeObserver.observe(root.value)
  window.addEventListener('resize', resize)
})
watch(() => [props.labels, props.series], render, { deep: true })
onBeforeUnmount(() => { resizeObserver?.disconnect(); window.removeEventListener('resize', resize); chart?.dispose() })
</script>

<template><div ref="root" class="chart" :class="{ 'chart--compact': compact }" role="img" aria-label="Data comparison chart" /></template>
