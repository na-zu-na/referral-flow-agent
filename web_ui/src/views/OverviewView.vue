<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, CircleCheck, Lock, Warning } from '@element-plus/icons-vue'
import { api, type Row } from '../api'

const loading = ref(true)
const error = ref('')
const cases = ref<Row[]>([])
const evidence = ref<Row>({})
const negativeCount = computed(() => cases.value.filter((item) => item.negative_case).length)
const modelCount = computed(() => new Set((evidence.value.d5?.models || []).map((item: Row) => item.model)).size)

async function load() {
  loading.value = true; error.value = ''
  try {
    const [caseData, evidenceData] = await Promise.all([api.cases(), api.evidence()])
    cases.value = caseData.items; evidence.value = evidenceData
  } catch (exc: any) { error.value = exc.message }
  finally { loading.value = false }
}
onMounted(load)

const steps = [
  ['01', '读取 Referral', '获取转诊信息与临床摘要'],
  ['02', '验证临床标准', '识别紧急程度、红旗与必要检查'],
  ['03', '查询患者与号源', '排除重复预约并限定合法时间窗口'],
  ['04', '安全决策', '预约、请求补充信息或升级处理'],
]
</script>

<template>
  <div v-loading="loading">
    <el-alert v-if="error" :title="error" type="error" show-icon class="page-alert"><template #default><el-button link @click="load">重试</el-button></template></el-alert>
    <section class="hero">
      <div>
        <el-tag effect="plain" round>Evidence-grounded referral workflow</el-tag>
        <h2>让每一次转诊决策<br><span>可执行、可阻断、可审计</span></h2>
        <p>系统连接现有案例、工具与 Guardrail，完整展示 Agent 如何从 referral 走到最终决策。</p>
        <router-link to="/run"><el-button type="primary" size="large">开始运行案例<el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button></router-link>
      </div>
      <div class="hero-signal" aria-label="系统安全摘要">
        <div class="signal-orbit"><el-icon><Lock /></el-icon></div>
        <strong>Safety first</strong><span>Booking Gate + Human Confirmation</span>
      </div>
    </section>

    <section class="metric-grid">
      <div class="metric"><span>评估案例</span><strong>{{ cases.length || '—' }}</strong><small>JSON fixtures</small></div>
      <div class="metric negative"><span>Negative cases</span><strong>{{ negativeCount || '—' }}</strong><small>失败边界与安全阻断</small></div>
      <div class="metric"><span>已评估模型</span><strong>{{ modelCount || '—' }}</strong><small>现有 D5 结果</small></div>
      <div class="metric"><span>证据模块</span><strong>4</strong><small>D2 · D4 · D5 · D7</small></div>
    </section>

    <section class="section-block">
      <div class="section-heading"><div><span class="eyebrow">Agent workflow</span><h3>从证据到决策</h3></div><p>不跳过前置检查，不让模型自行授权预约。</p></div>
      <div class="workflow">
        <div v-for="step in steps" :key="step[0]" class="workflow-step"><span>{{ step[0] }}</span><strong>{{ step[1] }}</strong><p>{{ step[2] }}</p></div>
      </div>
    </section>

    <section class="safety-callout">
      <div class="callout-icon"><el-icon><Warning /></el-icon></div>
      <div><span class="eyebrow">Negative-case demonstration</span><h3>系统能够明确地说“不”</h3><p>REF-5703 在 referral 自由文本中嵌入了跳过检查的指令。Guardrail 将其识别为不可信输入，安全停止且不会预约。</p></div>
      <router-link :to="{ path: '/run', query: { case: 'REF-5703' } }"><el-button>演示负面案例</el-button></router-link>
    </section>

    <section class="guardrail-list">
      <div v-for="item in ['Prompt injection 检测','Red flag 检测','科室匹配','必要检查','重复预约','号源窗口','人工确认']" :key="item"><el-icon><CircleCheck /></el-icon>{{ item }}</div>
    </section>
  </div>
</template>
