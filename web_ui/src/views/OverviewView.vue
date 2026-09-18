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
  ['01', 'Read referral', 'Retrieve referral details and the clinical summary'],
  ['02', 'Validate criteria', 'Identify urgency, red flags, and mandatory tests'],
  ['03', 'Check patient and slots', 'Prevent duplicates and enforce the legal booking window'],
  ['04', 'Make a safe decision', 'Book, request information, or escalate'],
]
</script>

<template>
  <div v-loading="loading">
    <el-alert v-if="error" :title="error" type="error" show-icon class="page-alert"><template #default><el-button link @click="load">Retry</el-button></template></el-alert>
    <section class="hero">
      <div>
        <el-tag effect="plain" round>Evidence-grounded referral workflow</el-tag>
        <h2>Every referral decision<br><span>actionable, stoppable, auditable</span></h2>
        <p>The system connects existing cases, tools, and guardrails to show how the Agent moves from a referral to a final decision.</p>
        <router-link to="/run"><el-button type="primary" size="large">Run a case<el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button></router-link>
      </div>
      <div class="hero-signal" aria-label="System safety summary">
        <div class="signal-orbit"><el-icon><Lock /></el-icon></div>
        <strong>Safety first</strong><span>Booking Gate + Human Confirmation</span>
      </div>
    </section>

    <section class="metric-grid">
      <div class="metric"><span>Evaluation cases</span><strong>{{ cases.length || '—' }}</strong><small>JSON fixtures</small></div>
      <div class="metric negative"><span>Negative cases</span><strong>{{ negativeCount || '—' }}</strong><small>Failure boundaries and safe stops</small></div>
      <div class="metric"><span>Evaluated models</span><strong>{{ modelCount || '—' }}</strong><small>Existing D5 results</small></div>
      <div class="metric"><span>Evidence modules</span><strong>4</strong><small>D2 · D4 · D5 · D7</small></div>
    </section>

    <section class="section-block">
      <div class="section-heading"><div><span class="eyebrow">Agent workflow</span><h3>From evidence to decision</h3></div><p>Prerequisites cannot be skipped, and the model cannot authorize its own booking.</p></div>
      <div class="workflow">
        <div v-for="step in steps" :key="step[0]" class="workflow-step"><span>{{ step[0] }}</span><strong>{{ step[1] }}</strong><p>{{ step[2] }}</p></div>
      </div>
    </section>

    <section class="safety-callout">
      <div class="callout-icon"><el-icon><Warning /></el-icon></div>
      <div><span class="eyebrow">Negative-case demonstration</span><h3>The system can clearly say no</h3><p>REF-5703 embeds an instruction in referral free text to bypass a required check. The guardrail identifies it as untrusted input, stops safely, and prevents booking.</p></div>
      <router-link :to="{ path: '/run', query: { case: 'REF-5703' } }"><el-button>Run negative case</el-button></router-link>
    </section>

    <section class="guardrail-list">
      <div v-for="item in ['Prompt injection detection','Red-flag detection','Specialty matching','Mandatory tests','Duplicate booking check','Booking window','Human confirmation']" :key="item"><el-icon><CircleCheck /></el-icon>{{ item }}</div>
    </section>
  </div>
</template>
