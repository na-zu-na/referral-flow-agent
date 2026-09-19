<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { api, formatCost, formatNumber, type Row } from '../api'

const loading = ref(true)
const detailLoading = ref(false)
const error = ref('')
const rows = ref<Row[]>([])
const selected = ref<Row | null>(null)
const toolCalls = ref<Row[]>([])
const drawer = ref(false)
const modelOptions = ref<string[]>([])
const filters = reactive({ case_id: '', model: '', passed: '', negative_case: '', limit: 100 })

const statusType = (status: string) => status === 'completed' ? 'success' : status === 'guardrail_stopped' ? 'warning' : status?.includes('invalid') || status === 'failed' ? 'danger' : 'info'
const passLabel = (value: unknown) => value === true ? 'Passed' : value === false ? 'Failed' : 'Pending review'
const passedCount = computed(() => rows.value.filter((row) => row.passed === true).length)

async function load() {
  loading.value = true; error.value = ''
  try {
    const data = await api.auditRuns(filters)
    rows.value = data.items
    modelOptions.value = data.models
  } catch (exc: any) { error.value = exc.message }
  finally { loading.value = false }
}

function reset() {
  Object.assign(filters, { case_id: '', model: '', passed: '', negative_case: '', limit: 100 }); load()
}

async function showDetail(row: Row) {
  selected.value = row; toolCalls.value = []; drawer.value = true; detailLoading.value = true
  try { toolCalls.value = (await api.toolCalls(row.run_id)).items }
  catch (exc: any) { error.value = exc.message }
  finally { detailLoading.value = false }
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <div class="page-intro"><div><span class="eyebrow">Traceability</span><h2>Run-level and tool-call audit logs</h2><p>Inspect existing live evaluation records and trace the model, prompt, descriptor, decision, cost, and each tool call.</p></div></div>
    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" />
    <section class="panel audit-panel">
      <el-form :inline="true" class="audit-filters" @submit.prevent="load">
        <el-form-item label="Case ID"><el-input v-model="filters.case_id" placeholder="REF-5703" clearable /></el-form-item>
        <el-form-item label="Model"><el-select v-model="filters.model" placeholder="All models" clearable filterable><el-option v-for="model in modelOptions" :key="model" :label="model" :value="model" /></el-select></el-form-item>
        <el-form-item label="Passed"><el-select v-model="filters.passed" placeholder="All results" clearable><el-option label="Passed" value="true" /><el-option label="Failed" value="false" /></el-select></el-form-item>
        <el-form-item label="Case type"><el-select v-model="filters.negative_case" placeholder="All case types" clearable><el-option label="Negative" value="true" /><el-option label="Positive" value="false" /></el-select></el-form-item>
        <el-form-item><el-button native-type="submit" type="primary" :icon="Search" :loading="loading">Search</el-button><el-button @click="reset">Reset</el-button></el-form-item>
      </el-form>
      <div class="table-summary"><span>{{ rows.length }} records shown</span><span>{{ passedCount }} passed</span><small>Click a row to inspect its tool calls</small></div>
      <el-table v-loading="loading" :data="rows" stripe row-key="run_id" class="clickable-table" @row-click="showDetail">
        <template #empty><el-empty description="No audit records match the current filters." /></template>
        <el-table-column prop="case_id" label="Case" width="105" fixed><template #default="{row}"><strong>{{ row.case_id }}</strong><el-tag v-if="row.negative_case" type="danger" size="small" effect="plain" class="cell-tag">NEG</el-tag></template></el-table-column>
        <el-table-column prop="model" label="Model" min-width="205" show-overflow-tooltip />
        <el-table-column label="Policy" min-width="150"><template #default="{row}"><span class="policy-cell">{{ row.prompt_version }} / {{ row.descriptor_version }}<small>{{ row.execution_mode }}</small></span></template></el-table-column>
        <el-table-column label="Decision" min-width="150"><template #default="{row}"><span>{{ row.expected_decision }} → <strong>{{ row.decision || '—' }}</strong></span></template></el-table-column>
        <el-table-column label="Result" width="105"><template #default="{row}"><el-tag :type="row.passed === true ? 'success' : row.passed === false ? 'danger' : 'info'" size="small">{{ passLabel(row.passed) }}</el-tag></template></el-table-column>
        <el-table-column label="Status" min-width="145"><template #default="{row}"><el-tag :type="statusType(row.status)" effect="plain" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="turns" label="Turns" width="72" />
        <el-table-column label="Tokens" width="110"><template #default="{row}">{{ formatNumber((row.tokens_in || 0) + (row.tokens_out || 0), 0) }}</template></el-table-column>
        <el-table-column label="Cost" width="115"><template #default="{row}">{{ formatCost(row.cost_usd) }}</template></el-table-column>
        <el-table-column prop="timestamp" label="Timestamp" min-width="180" show-overflow-tooltip />
      </el-table>
    </section>

    <el-drawer v-model="drawer" size="min(760px, 94vw)" title="Run audit detail">
      <div v-if="selected" class="drawer-content" v-loading="detailLoading">
        <div class="drawer-title"><div><span class="eyebrow">{{ selected.run_id }}</span><h3>{{ selected.case_id }}</h3></div><el-tag :type="statusType(selected.status)">{{ selected.status }}</el-tag></div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Model" :span="2">{{ selected.model }}</el-descriptions-item>
          <el-descriptions-item label="Prompt">{{ selected.prompt_version }}</el-descriptions-item><el-descriptions-item label="Descriptor">{{ selected.descriptor_version }}</el-descriptions-item>
          <el-descriptions-item label="Execution">{{ selected.execution_mode }}</el-descriptions-item><el-descriptions-item label="Autonomy">{{ selected.autonomy || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Temperature">{{ selected.temperature ?? '—' }}</el-descriptions-item><el-descriptions-item label="Backend">{{ selected.backend }}</el-descriptions-item>
          <el-descriptions-item label="Expected">{{ selected.expected_decision }}</el-descriptions-item><el-descriptions-item label="Actual">{{ selected.decision || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Cost">{{ formatCost(selected.cost_usd) }}</el-descriptions-item><el-descriptions-item label="Cost source">{{ selected.cost_source || '—' }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.provider_cost_usd != null" label="Provider cost">{{ formatCost(selected.provider_cost_usd) }}</el-descriptions-item><el-descriptions-item v-if="selected.calculated_cost_usd != null" label="Calculated cost">{{ formatCost(selected.calculated_cost_usd) }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.cached_input_tokens != null" label="Cached tokens">{{ formatNumber(selected.cached_input_tokens, 0) }}</el-descriptions-item><el-descriptions-item v-if="selected.reasoning_tokens != null" label="Reasoning tokens">{{ formatNumber(selected.reasoning_tokens, 0) }}</el-descriptions-item>
          <el-descriptions-item label="Prompt hash" :span="2"><code>{{ selected.prompt_hash || '—' }}</code></el-descriptions-item>
          <el-descriptions-item v-if="selected.failure_reason" label="Failure" :span="2">{{ selected.failure_reason }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.error" label="Error" :span="2">{{ selected.error }}</el-descriptions-item>
        </el-descriptions>
        <div class="subsection-heading"><div><h4>Tool-call log</h4><p>Observation size is the cost lever used in D2(b)/D6.</p></div><el-tag effect="plain">{{ toolCalls.length }} calls</el-tag></div>
        <el-table :data="toolCalls" stripe><template #empty><el-empty description="This run has no tool-call records." /></template><el-table-column prop="turn" label="Turn" width="65" /><el-table-column prop="tool_name" label="Tool" min-width="160" /><el-table-column prop="descriptor_version" label="Descriptor" width="100" /><el-table-column prop="observation_tokens" label="Obs. tokens" width="105" /><el-table-column prop="observation_chars" label="Obs. chars" width="100" /><el-table-column label="Latency" width="100"><template #default="{row}">{{ row.latency_ms == null ? '—' : `${formatNumber(row.latency_ms, 2)} ms` }}</template></el-table-column><el-table-column label="OK" width="65"><template #default="{row}"><el-tag :type="row.ok ? 'success' : 'danger'" size="small">{{ row.ok ? 'Yes' : 'No' }}</el-tag></template></el-table-column></el-table>
      </div>
    </el-drawer>
  </div>
</template>
