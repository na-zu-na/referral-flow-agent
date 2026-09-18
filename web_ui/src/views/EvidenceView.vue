<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, formatCost, formatNumber, formatPercent, type Row } from '../api'
import BarChart from '../components/BarChart.vue'

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
const d7Rows = computed(() => [evidence.value.d7?.failure_1, evidence.value.d7?.failure_2].filter(Boolean))
</script>

<template>
  <div class="page-stack" v-loading="loading">
    <div class="page-intro"><div><span class="eyebrow">Evaluation evidence</span><h2>现有实验结果</h2><p>只读展示项目中已有的 D2、D4、D5 与 D7 证据，不重新运行模型或生成替代数据。</p></div></div>
    <el-alert v-if="error" :title="error" type="error" show-icon><template #default><el-button link @click="load">重试</el-button></template></el-alert>
    <section v-if="!error" class="panel evidence-panel">
      <el-tabs v-model="tab">
        <el-tab-pane label="D2 · Tool design" name="d2">
          <div class="evidence-heading"><div><h3>描述符与执行模式</h3><p>对比并行/串行调用、工具描述符版本与 observation size。</p></div><el-tag effect="plain">{{ d2.length }} variants</el-tag></div>
          <el-empty v-if="!d2.length" description="没有现有 D2 数据" />
          <template v-else>
            <div class="chart-grid">
              <div class="chart-card"><h4>Average turns</h4><BarChart :labels="d2.map(x => shortVariant(x.variant))" :series="[{ name: 'Avg turns', data: d2.map(x => Number(x.avg_turns)), color: '#176b87' }]" /></div>
              <div class="chart-card"><h4>Observation tokens</h4><BarChart :labels="d2.map(x => shortVariant(x.variant))" :series="[{ name: 'Estimated tokens', data: d2.map(x => Number(x.avg_tool_return_tokens_estimated_chars_div_4)), color: '#d58b36' }]" /></div>
            </div>
            <el-table :data="d2" stripe><el-table-column prop="variant" label="Variant" min-width="210" /><el-table-column prop="runs" label="Runs" width="80" /><el-table-column label="Pass rate" width="110"><template #default="{row}">{{ formatPercent(row.pass_rate) }}</template></el-table-column><el-table-column prop="avg_turns" label="Avg turns" width="110" /><el-table-column label="Observation tokens" min-width="150"><template #default="{row}">{{ formatNumber(row.avg_tool_return_tokens_estimated_chars_div_4) }}</template></el-table-column></el-table>
          </template>
        </el-tab-pane>

        <el-tab-pane label="D4 · Policy" name="d4">
          <div class="evidence-heading"><div><h3>Prompt / Policy 对比</h3><p>展示现有 V1/V2 policy 的最终通过率与 negative-case 通过率。</p></div></div>
          <el-empty v-if="!d4.length" description="没有现有 D4 数据" />
          <template v-else>
            <div class="chart-card chart-wide"><h4>Outcome comparison</h4><BarChart :labels="d4.map((_, i) => `Policy ${i + 1}`)" percent :series="[{ name: 'Final pass', data: d4.map(x => Number(x.final_pass_rate)), color: '#176b87' }, { name: 'Negative pass', data: d4.map(x => Number(x.negative_final_pass_rate)), color: '#d58b36' }]" /></div>
            <el-table :data="d4" stripe><el-table-column prop="policy" label="Policy" min-width="360" /><el-table-column prop="runs" label="Runs" width="80" /><el-table-column label="Final pass" width="110"><template #default="{row}">{{ formatPercent(row.final_pass_rate) }}</template></el-table-column><el-table-column label="Negative pass" width="130"><template #default="{row}">{{ formatPercent(row.negative_final_pass_rate) }}</template></el-table-column><el-table-column label="Diagnostic clean" width="140"><template #default="{row}">{{ formatPercent(row.diagnostic_clean_rate) }}</template></el-table-column></el-table>
          </template>
        </el-tab-pane>

        <el-tab-pane label="D5 · Models & cost" name="d5">
          <div class="evidence-heading"><div><h3>模型性能与实际成本</h3><p>Cost 保留源文件的 cost source；不存在的测量值不显示为零。</p></div><el-tag effect="plain">{{ d5.length }} model runs</el-tag></div>
          <el-empty v-if="!d5.length" description="没有现有 D5 数据" />
          <template v-else>
            <div class="chart-grid">
              <div class="chart-card"><h4>Pass rate</h4><BarChart :labels="d5.map(x => shortModel(x.model))" percent :series="[{ name: 'Final pass', data: d5.map(x => Number(x.final_pass_rate)), color: '#176b87' }, { name: 'Negative pass', data: d5.map(x => Number(x.negative_final_pass_rate)), color: '#d58b36' }]" /></div>
              <div class="chart-card"><h4>Cost (USD)</h4><BarChart :labels="d5.map(x => shortModel(x.model))" :series="[{ name: 'Cost USD', data: d5.map(x => Number(x.cost_usd)), color: '#5d6fc1' }]" /></div>
            </div>
            <el-table :data="d5" stripe><el-table-column prop="model" label="Exact model ID" min-width="210" fixed /><el-table-column prop="runs" label="Runs" width="70" /><el-table-column label="Final pass" width="105"><template #default="{row}">{{ formatPercent(row.final_pass_rate) }}</template></el-table-column><el-table-column label="Negative pass" width="125"><template #default="{row}">{{ formatPercent(row.negative_final_pass_rate) }}</template></el-table-column><el-table-column prop="unsafe_booking_attempts" label="Unsafe bookings" width="130" /><el-table-column label="Tokens in/out" min-width="150"><template #default="{row}">{{ formatNumber(row.tokens_in, 0) }} / {{ formatNumber(row.tokens_out, 0) }}</template></el-table-column><el-table-column label="Cost" width="120"><template #default="{row}">{{ formatCost(row.cost_usd) }}</template></el-table-column><el-table-column prop="cost_source" label="Cost source" min-width="150" /><el-table-column label="Mean turns" width="110"><template #default="{row}">{{ formatNumber(row.mean_turns) }}</template></el-table-column></el-table>
          </template>
        </el-tab-pane>

        <el-tab-pane label="D7 · Failures" name="d7">
          <div class="evidence-heading"><div><h3>受控失败与修复</h3><p>两个已有的失败边界，并列展示删除关键组件后与恢复后的结果。</p></div></div>
          <el-empty v-if="!evidence.d7" description="没有现有 D7 数据" />
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
