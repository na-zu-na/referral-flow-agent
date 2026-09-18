<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api, formatCost, formatNumber, type Row } from '../api'

const route = useRoute()
const cases = ref<Row[]>([])
const loadingCases = ref(true)
const submitting = ref(false)
const confirmationSubmitting = ref(false)
const confirmationOpen = ref(false)
const error = ref('')
const job = ref<Row | null>(null)
let timer: number | undefined

const form = reactive({
  case_id: String(route.query.case || 'REF-5602'), backend: 'scripted', model: '',
  prompt_version: 'v2', descriptor_version: 'v2', execution_mode: 'parallel',
  autonomy: 'confirm', temperature: 0,
})
const filters = reactive({ tier: 'all', kind: 'all' })
const filteredCases = computed(() => cases.value.filter((item) =>
  (filters.tier === 'all' || item.evaluation_tier === filters.tier)
  && (filters.kind === 'all' || String(item.negative_case) === filters.kind),
))
const selectedCase = computed(() => cases.value.find((item) => item.case_id === form.case_id))
const isActive = computed(() => Boolean(job.value && !job.value.finished))
const record = computed(() => job.value?.record)
const observations = computed(() => new Map<string, Row>((record.value?.observations || []).map((item: Row) => [item.call_id, item])))
const confirmation = computed(() => job.value?.confirmation?.call?.arguments || {})

const statusMap: Record<string, { label: string; type: 'success' | 'warning' | 'danger' | 'info' | 'primary' }> = {
  queued: { label: 'Queued', type: 'info' }, running: { label: 'Running', type: 'primary' },
  confirmation_required: { label: 'Awaiting human confirmation', type: 'warning' },
  confirmation_rejected: { label: 'Rejected by human', type: 'warning' }, completed: { label: 'Completed', type: 'success' },
  guardrail_stopped: { label: 'Stopped safely by guardrail', type: 'warning' }, failed: { label: 'Run failed', type: 'danger' },
}
const status = computed(() => statusMap[job.value?.status] || { label: job.value?.status || 'Not started', type: 'info' as const })

async function loadCases() {
  loadingCases.value = true
  try {
    cases.value = (await api.cases()).items
    if (!cases.value.some((item) => item.case_id === form.case_id)) form.case_id = cases.value[0]?.case_id || ''
  } catch (exc: any) { error.value = exc.message }
  finally { loadingCases.value = false }
}

function chooseScenario(caseId: string) {
  if (!isActive.value) form.case_id = caseId
}

async function poll() {
  if (!job.value?.job_id) return
  try {
    job.value = await api.run(job.value.job_id)
    if (job.value.status === 'confirmation_required') confirmationOpen.value = true
    if (!job.value.finished) timer = window.setTimeout(poll, 500)
  } catch (exc: any) { error.value = exc.message }
}

async function startRun() {
  if (!form.case_id) return
  if (form.backend === 'live' && !form.model.trim()) {
    error.value = 'Live backend requires an exact model ID.'; return
  }
  window.clearTimeout(timer); submitting.value = true; error.value = ''; job.value = null
  try {
    job.value = await api.createRun({ ...form, model: form.backend === 'live' ? form.model.trim() : null })
    await poll()
  } catch (exc: any) { error.value = exc.message }
  finally { submitting.value = false }
}

async function submitConfirmation(approved: boolean) {
  if (!job.value) return
  confirmationSubmitting.value = true
  try {
    await api.confirm(job.value.job_id, approved)
    confirmationOpen.value = false
    ElMessage.success(approved ? 'Booking approved.' : 'Booking rejected.')
    await poll()
  } catch (exc: any) { error.value = exc.message }
  finally { confirmationSubmitting.value = false }
}

onMounted(loadCases)
onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<template>
  <div class="page-stack">
    <div class="page-intro">
      <div><span class="eyebrow">Live workflow</span><h2>Run a complete Agent decision</h2><p>Select a case and configuration, then observe tool calls, guardrails, and the final decision in real time.</p></div>
      <div class="scenario-buttons"><el-button :disabled="isActive" @click="chooseScenario('REF-5602')">Safe booking</el-button><el-button type="warning" plain :disabled="isActive" @click="chooseScenario('REF-5703')">Negative case</el-button></div>
    </div>
    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" />

    <div class="run-layout">
      <section class="panel run-config" v-loading="loadingCases">
        <div class="panel-heading"><div><span class="step-label">STEP 1</span><h3>Configure run</h3></div><el-tag v-if="selectedCase?.negative_case" type="danger" effect="light">Negative case</el-tag></div>
        <el-form label-position="top" @submit.prevent="startRun">
          <div class="filter-row">
            <el-select v-model="filters.tier" aria-label="Case tier"><el-option label="All tiers" value="all" /><el-option label="Core" value="core" /><el-option label="Extended" value="extended" /></el-select>
            <el-select v-model="filters.kind" aria-label="Case type"><el-option label="All case types" value="all" /><el-option label="Positive" value="false" /><el-option label="Negative" value="true" /></el-select>
          </div>
          <el-form-item label="Referral case" required>
            <el-select v-model="form.case_id" filterable :disabled="isActive" class="full-width">
              <el-option v-for="item in filteredCases" :key="item.case_id" :label="`${item.case_id} · ${item.design_purpose}`" :value="item.case_id"><span>{{ item.case_id }} · {{ item.design_purpose }}</span><span v-if="item.negative_case" class="option-danger">NEG</span></el-option>
            </el-select>
          </el-form-item>
          <div v-if="selectedCase" class="case-summary">
            <div><el-tag size="small" effect="plain">{{ selectedCase.evaluation_tier }}</el-tag><span>{{ selectedCase.source }}</span></div>
            <strong>{{ selectedCase.design_purpose }}</strong><p>{{ selectedCase.input_summary }}</p>
          </div>
          <div class="form-grid">
            <el-form-item label="Backend"><el-select v-model="form.backend" :disabled="isActive"><el-option label="Scripted" value="scripted" /><el-option label="Live model" value="live" /></el-select></el-form-item>
            <el-form-item label="Autonomy"><el-select v-model="form.autonomy" :disabled="isActive"><el-option label="Confirm" value="confirm" /><el-option label="Suggest" value="suggest" /><el-option label="Act" value="act" /></el-select></el-form-item>
            <el-form-item label="Prompt"><el-segmented v-model="form.prompt_version" :options="['v1','v2']" :disabled="isActive" /></el-form-item>
            <el-form-item label="Descriptor"><el-segmented v-model="form.descriptor_version" :options="['v1','v2']" :disabled="isActive" /></el-form-item>
            <el-form-item label="Execution"><el-select v-model="form.execution_mode" :disabled="isActive"><el-option label="Parallel" value="parallel" /><el-option label="Sequential" value="sequential" /></el-select></el-form-item>
            <el-form-item label="Temperature"><el-input-number v-model="form.temperature" :min="0" :step="0.1" :disabled="isActive" /></el-form-item>
          </div>
          <el-form-item v-if="form.backend === 'live'" label="Exact model ID" required><el-input v-model="form.model" placeholder="openai/gpt-4o-mini" :disabled="isActive" /><div class="form-help">The API key is read only from the backend environment.</div></el-form-item>
          <el-button native-type="submit" type="primary" size="large" class="full-width" :loading="submitting" :disabled="isActive || !form.case_id">{{ isActive ? 'Agent is running' : 'Run Agent' }}</el-button>
        </el-form>
      </section>

      <section class="panel run-output">
        <div class="panel-heading"><div><span class="step-label">STEP 2</span><h3>Run trace</h3></div><el-tag :type="status.type" effect="light" round>{{ status.label }}</el-tag></div>
        <el-empty v-if="!job" description="Configure a case and start the Agent to view the complete execution trace." />
        <template v-else>
          <div class="run-meta"><span>Job {{ job.job_id }}</span><span>{{ job.case_id }}</span><span v-if="job.updated_at">Updated {{ new Date(job.updated_at).toLocaleTimeString() }}</span></div>
          <el-progress v-if="isActive" :percentage="job.status === 'confirmation_required' ? 80 : 45" :indeterminate="job.status !== 'confirmation_required'" :duration="2" />

          <div v-if="record?.final" class="decision-card" :class="record.final.decision">
            <div><span class="eyebrow">Final decision</span><h3>{{ record.final.decision }}</h3><p>{{ record.final.reason }}</p></div>
            <div class="decision-result"><span>Expected: {{ job.expected?.decision || '—' }}</span><el-tag :type="job.evaluation?.passed === false ? 'danger' : job.evaluation?.passed === true ? 'success' : 'info'">{{ job.evaluation?.passed === true ? 'Evaluation passed' : job.evaluation?.passed === false ? 'Evaluation failed' : 'Pending human review' }}</el-tag></div>
          </div>
          <el-alert v-if="record?.stopped_by" :title="record.stopped_by.code" :description="record.stopped_by.message" type="warning" show-icon :closable="false" class="result-alert" />
          <el-alert v-if="job.error" :title="job.error.type" :description="job.error.message" type="error" show-icon :closable="false" class="result-alert" />

          <div v-if="record" class="run-metrics">
            <div><span>Turns</span><strong>{{ formatNumber(record.turns, 0) }}</strong></div>
            <div v-if="record.tokens_in != null"><span>Tokens in</span><strong>{{ formatNumber(record.tokens_in, 0) }}</strong></div>
            <div v-if="record.tokens_out != null"><span>Tokens out</span><strong>{{ formatNumber(record.tokens_out, 0) }}</strong></div>
            <div v-if="record.cost_usd != null"><span>Cost</span><strong>{{ formatCost(record.cost_usd) }}</strong></div>
            <div v-if="record.latency_ms != null"><span>Latency</span><strong>{{ formatNumber(record.latency_ms, 1) }} ms</strong></div>
          </div>

          <div v-if="record?.tool_calls?.length" class="timeline">
            <h4>Tool-call timeline</h4>
            <div v-for="call in record.tool_calls" :key="call.id" class="timeline-item">
              <div class="timeline-marker">{{ call.turn }}</div>
              <div class="timeline-content">
                <div class="timeline-title"><strong>{{ call.name }}</strong><el-tag size="small" :type="call.ok ? 'success' : 'danger'">{{ call.ok ? 'OK' : call.error_code }}</el-tag></div>
                <div class="timeline-meta"><span>{{ call.observation_tokens }} observation tokens</span><span v-if="call.latency_ms != null">{{ formatNumber(call.latency_ms, 2) }} ms</span></div>
                <el-collapse><el-collapse-item title="View arguments and observation"><div class="json-grid"><div><small>Arguments</small><pre>{{ JSON.stringify(call.arguments, null, 2) }}</pre></div><div><small>Observation</small><pre>{{ JSON.stringify(observations.get(call.id)?.result, null, 2) }}</pre></div></div></el-collapse-item></el-collapse>
              </div>
            </div>
          </div>
          <div v-if="record?.guardrail_events?.length" class="guardrail-events"><h4>Guardrail events</h4><div v-for="event in record.guardrail_events" :key="event.code" class="event-row"><el-tag type="warning">{{ event.code }}</el-tag><span>{{ event.message }}</span></div></div>
        </template>
      </section>
    </div>

    <el-dialog v-model="confirmationOpen" title="Human booking confirmation" width="min(520px, 92vw)" :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
      <el-alert title="The Agent is about to perform an irreversible booking action." type="warning" show-icon :closable="false" />
      <el-descriptions :column="2" border class="confirmation-details">
        <el-descriptions-item label="Referral">{{ confirmation.referral_id }}</el-descriptions-item><el-descriptions-item label="Clinic">{{ confirmation.clinic }}</el-descriptions-item>
        <el-descriptions-item label="Specialty">{{ confirmation.specialty }}</el-descriptions-item><el-descriptions-item label="Band">{{ confirmation.band }}</el-descriptions-item>
        <el-descriptions-item label="Date">{{ confirmation.date }}</el-descriptions-item><el-descriptions-item label="Time">{{ confirmation.time }}</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button :disabled="confirmationSubmitting" @click="submitConfirmation(false)">Reject booking</el-button><el-button type="primary" :loading="confirmationSubmitting" @click="submitConfirmation(true)">Approve booking</el-button></template>
    </el-dialog>
  </div>
</template>
