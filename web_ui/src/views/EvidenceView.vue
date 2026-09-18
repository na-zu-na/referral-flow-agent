<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, formatCost, formatNumber, formatPercent, type Row } from '../api'
import BarChart from '../components/BarChart.vue'
import { formatDelta, normalizePolicies, percentagePointDelta, policiesMatch, POLICY_METRICS, summarizePolicies, type PolicyRow } from '../policy'

const loading = ref(true)
const error = ref('')
const evidence = ref<Row>({})
const tab = ref('d2')

async function load() {
  loading.value = true; error.value = ''
  try { evidence.value = await api.evidence() }
  catch (exc: any) { error.value = exc.message }
  finally { loading.value = false }
}
onMounted(load)

const d2 = computed<Row[]>(() => evidence.value.d2?.variants || [])
const d4 = computed<Row[]>(() => evidence.value.d4?.policies || [])
const d5 = computed<Row[]>(() => evidence.value.d5?.models || [])
const shortVariant = (value: string) => value?.replace('callmode_', '').replace('descriptor_', '') || '—'
const shortModel = (value: string) => value?.split('/').pop()?.replaceAll('-', ' ') || '—'
const promptComparisonModels = computed(() => [...new Set(d5.value.filter((row) => d5.value.filter((other) => other.model === row.model).length > 1).map((row) => row.model))])
const isPromptComparison = (row: Row) => promptComparisonModels.value.includes(row.model)
const promptVersion = (row: Row) => row.prompt_version || `v${d5.value.filter((item) => item.model === row.model).indexOf(row) + 1}`
const promptLabel = (row: Row) => `Prompt ${promptVersion(row).toUpperCase()}${promptVersion(row) === 'v1' ? ' (Control)' : ''}`
const modelExperimentLabel = (row: Row) => {
  const name = shortModel(row.model)
  if (!isPromptComparison(row)) return name
  return `Qwen · Prompt ${promptVersion(row).toUpperCase()}`
}
const d7Rows = computed(() => [evidence.value.d7?.failure_1, evidence.value.d7?.failure_2].filter(Boolean))

const policyMetrics = POLICY_METRICS
const policies = computed(() => normalizePolicies(d4.value))
const baseline = computed(() => policies.value[0])
const current = computed(() => policies.value.at(-1))
const policyDelta = (row: PolicyRow | undefined, key: string) => percentagePointDelta(row, baseline.value, key)
const deltaTone = (value: number) => value > 0.05 ? 'positive' : value < -0.05 ? 'negative' : 'neutral'
const policiesEqual = computed(() => policiesMatch(policies.value))
const policySummary = computed(() => summarizePolicies(policies.value))
const titleCase = (value: unknown) => String(value || '—').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
</script>

<template>
  <div class="page-stack" v-loading="loading">
    <div class="page-intro"><div><span class="eyebrow">Evaluation evidence</span><h2>Existing experiment results</h2><p>Read-only evidence from D2, D4, D5, and D7. This page does not rerun models or generate substitute data.</p></div></div>
    <el-alert v-if="error" :title="error" type="error" show-icon><template #default><el-button link @click="load">Retry</el-button></template></el-alert>
    <section v-if="!error" class="panel evidence-panel">
      <el-tabs v-model="tab">
        <el-tab-pane label="D2 · Tool design" name="d2">
          <div class="evidence-heading"><div><h3>Descriptors and execution modes</h3><p>Compare parallel and sequential calls, descriptor versions, and observation size.</p></div><el-tag effect="plain">{{ d2.length }} variants</el-tag></div>
          <el-empty v-if="!d2.length" description="No D2 data is available." />
          <template v-else>
            <div class="chart-grid">
              <div class="chart-card"><h4>Average turns</h4><BarChart :labels="d2.map(x => shortVariant(x.variant))" :series="[{ name: 'Avg turns', data: d2.map(x => Number(x.avg_turns)), color: '#176b87' }]" /></div>
              <div class="chart-card"><h4>Observation tokens</h4><BarChart :labels="d2.map(x => shortVariant(x.variant))" :series="[{ name: 'Estimated tokens', data: d2.map(x => Number(x.avg_tool_return_tokens_estimated_chars_div_4)), color: '#d58b36' }]" /></div>
            </div>
            <el-table :data="d2" stripe><el-table-column prop="variant" label="Variant" min-width="210" /><el-table-column prop="runs" label="Runs" width="80" /><el-table-column label="Pass rate" width="110"><template #default="{row}">{{ formatPercent(row.pass_rate) }}</template></el-table-column><el-table-column prop="avg_turns" label="Avg turns" width="110" /><el-table-column label="Observation tokens" min-width="150"><template #default="{row}">{{ formatNumber(row.avg_tool_return_tokens_estimated_chars_div_4) }}</template></el-table-column></el-table>
          </template>
        </el-tab-pane>

        <el-tab-pane label="D4 · Policy" name="d4">
          <div class="evidence-heading policy-heading"><div><h3>Prompt / Policy Comparison</h3><p>Compare final pass and negative-case pass rates for the existing V1 and V2 policies.</p></div></div>
          <el-empty v-if="!d4.length" description="No D4 data is available." />
          <template v-else>
            <div class="policy-summary" role="status"><div><span>SUMMARY</span><p>{{ policySummary }}</p></div><el-tag v-if="policiesEqual" type="success" effect="light">No measurable difference</el-tag></div>

            <div class="policy-kpis">
              <div v-for="metric in policyMetrics" :key="metric.key" class="policy-kpi">
                <span>{{ metric.label }}</span>
                <strong>{{ formatPercent(current?.[metric.key]) }}</strong>
                <small :class="deltaTone(policyDelta(current, metric.key))">{{ formatDelta(policyDelta(current, metric.key)) }} vs baseline</small>
              </div>
            </div>

            <div class="chart-card chart-wide policy-chart" :class="{ 'is-equal': policiesEqual }">
              <div class="policy-chart-heading"><div><h4>Outcome Comparison</h4><p>Policy outcomes by metric</p></div><span v-if="policiesEqual">No measurable difference between policies</span></div>
              <BarChart
                :labels="policyMetrics.map(metric => metric.label)"
                :series="policies.map((policy, index) => ({ name: policy.version, data: policyMetrics.map(metric => Number(policy[metric.key])), color: index === 0 ? '#9aabc0' : '#176b87' }))"
                percent horizontal show-values compact
              />
            </div>

            <div class="policy-table-heading"><div><h4>Policy Configuration</h4><p>Exact configuration used for each evaluated version.</p></div><el-tag effect="plain">{{ policies.length }} policies</el-tag></div>
            <el-table :data="policies" stripe class="policy-table">
              <el-table-column label="Version" width="145" fixed><template #default="{row, $index}"><strong>{{ row.version }}</strong><el-tag v-if="$index === 0" size="small" type="info" effect="plain" class="baseline-tag">Baseline</el-tag></template></el-table-column>
              <el-table-column label="Configuration" min-width="390"><template #default="{row}"><div class="config-tags"><el-tag size="small" effect="plain">Prompt {{ row.config.prompt_version }}</el-tag><el-tag size="small" effect="plain">Descriptor {{ row.config.descriptor_version }}</el-tag><el-tag size="small" effect="plain">{{ titleCase(row.config.call_mode) }}</el-tag><el-tag size="small" effect="plain">{{ titleCase(row.config.autonomy) }}</el-tag></div></template></el-table-column>
              <el-table-column prop="runs" label="Runs" width="80" />
              <el-table-column label="Final Pass" width="110"><template #default="{row}">{{ formatPercent(row.final_pass_rate) }}</template></el-table-column>
              <el-table-column label="Negative Pass" width="130"><template #default="{row}">{{ formatPercent(row.negative_final_pass_rate) }}</template></el-table-column>
              <el-table-column label="Diagnostic" width="110"><template #default="{row}">{{ formatPercent(row.diagnostic_clean_rate) }}</template></el-table-column>
              <el-table-column label="Δ Final" width="110"><template #default="{row, $index}"><span v-if="$index === 0" class="delta neutral">Baseline</span><span v-else class="delta" :class="deltaTone(policyDelta(row, 'final_pass_rate'))">{{ formatDelta(policyDelta(row, 'final_pass_rate'), false) }}</span></template></el-table-column>
            </el-table>
          </template>
        </el-tab-pane>

        <el-tab-pane label="D5 · Models & cost" name="d5">
          <div class="evidence-heading"><div><h3>Model performance and actual cost</h3><p>Cost retains the source file's cost source. Missing measurements are not displayed as zero.</p></div><el-tag effect="plain">{{ d5.length }} model runs</el-tag></div>
          <el-empty v-if="!d5.length" description="No D5 data is available." />
          <template v-else>
            <div v-if="promptComparisonModels.length" class="model-comparison-note"><strong>Prompt-version control:</strong> {{ promptComparisonModels.join(', ') }} appears more than once to compare Prompt V1 (Control) with Prompt V2 using the same model.</div>
            <div class="chart-grid">
              <div class="chart-card model-chart"><h4>Pass rate</h4><BarChart :labels="d5.map(modelExperimentLabel)" percent horizontal show-values compact wide-labels :series="[{ name: 'Final pass', data: d5.map(x => Number(x.final_pass_rate)), color: '#176b87' }, { name: 'Negative pass', data: d5.map(x => Number(x.negative_final_pass_rate)), color: '#d58b36' }]" /></div>
              <div class="chart-card model-chart"><h4>Cost (USD)</h4><BarChart :labels="d5.map(modelExperimentLabel)" horizontal show-values compact wide-labels :series="[{ name: 'Cost USD', data: d5.map(x => Number(x.cost_usd)), color: '#5d6fc1' }]" /></div>
            </div>
            <el-table :data="d5" stripe><el-table-column label="Exact model ID" min-width="235" fixed><template #default="{row}"><div class="model-id-cell"><span class="model-name-ellipsis" :title="row.model">{{ row.model }}</span><el-tag v-if="isPromptComparison(row)" :type="promptVersion(row) === 'v1' ? 'warning' : 'primary'" size="small" effect="plain">{{ promptLabel(row) }}</el-tag></div></template></el-table-column><el-table-column prop="runs" label="Runs" width="70" /><el-table-column label="Final pass" width="105"><template #default="{row}">{{ formatPercent(row.final_pass_rate) }}</template></el-table-column><el-table-column label="Negative pass" width="125"><template #default="{row}">{{ formatPercent(row.negative_final_pass_rate) }}</template></el-table-column><el-table-column prop="unsafe_booking_attempts" label="Unsafe bookings" width="130" /><el-table-column label="Tokens in/out" min-width="150"><template #default="{row}">{{ formatNumber(row.tokens_in, 0) }} / {{ formatNumber(row.tokens_out, 0) }}</template></el-table-column><el-table-column label="Cost" width="120"><template #default="{row}">{{ formatCost(row.cost_usd) }}</template></el-table-column><el-table-column prop="cost_source" label="Cost source" min-width="150" /><el-table-column label="Mean turns" width="110"><template #default="{row}">{{ formatNumber(row.mean_turns) }}</template></el-table-column></el-table>
          </template>
        </el-tab-pane>

        <el-tab-pane label="D7 · Failures" name="d7">
          <div class="evidence-heading"><div><h3>Controlled failures and fixes</h3><p>Two existing failure boundaries compare results after removing and restoring a critical component.</p></div></div>
          <el-empty v-if="!evidence.d7" description="No D7 data is available." />
          <template v-else>
            <div class="distribution-strip"><div><span>Core cases</span><strong>{{ evidence.d7.turn_distribution?.cases ?? '—' }}</strong></div><div><span>Pass rate</span><strong>{{ formatPercent(evidence.d7.turn_distribution?.pass_rate) }}</strong></div><div><span>Median turns</span><strong>{{ formatNumber(evidence.d7.turn_distribution?.median_turns) }}</strong></div><div><span>Recommended cap</span><strong>{{ evidence.d7.recommended_step_cap ?? '—' }}</strong></div></div>
            <article v-for="item in d7Rows" :key="item.failure" class="failure-case">
              <div class="failure-title"><div><el-tag type="danger" effect="plain">{{ item.failure }}</el-tag><h4>{{ item.deleted_component }}</h4></div><p>{{ item.success_criterion }}</p></div>
              <div class="failure-comparison">
                <div class="failure-state broken"><span>BROKEN</span><strong>{{ item.broken.status }}</strong><dl><dt>Stopped by</dt><dd>{{ item.broken.stopped_by || '—' }}</dd><dt>Turns</dt><dd>{{ item.broken.turns }}</dd><dt>Tokens</dt><dd>{{ formatNumber(item.broken.tokens_in + item.broken.tokens_out, 0) }}</dd><dt>Cost</dt><dd>{{ formatCost(item.broken.cost_usd) }}</dd></dl></div>
                <div class="comparison-arrow">→</div>
                <div class="failure-state fixed"><span>FIXED</span><strong>{{ item.fixed.status }}</strong><dl><dt>Stopped by</dt><dd>{{ item.fixed.stopped_by || '—' }}</dd><dt>Turns</dt><dd>{{ item.fixed.turns }}</dd><dt>Tokens</dt><dd>{{ formatNumber(item.fixed.tokens_in + item.fixed.tokens_out, 0) }}</dd><dt>Cost</dt><dd>{{ formatCost(item.fixed.cost_usd) }}</dd></dl></div>
              </div>
              <p class="finding">{{ item.finding }}</p>
            </article>
          </template>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>
