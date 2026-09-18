import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizePolicies, parsePolicy, percentagePointDelta, policiesMatch, summarizePolicies } from '../src/policy.ts'

const v1 = { policy: 'prompt_version=v1|descriptor_version=v1|call_mode=parallel|autonomy=confirm', runs: 52, final_pass_rate: 1, negative_final_pass_rate: 1, diagnostic_clean_rate: 1 }
const v2 = { policy: 'prompt_version=v2|descriptor_version=v2|call_mode=parallel|autonomy=confirm', runs: 52, final_pass_rate: 1, negative_final_pass_rate: 1, diagnostic_clean_rate: 1 }

test('parses configuration and summarizes equal policies', () => {
  assert.deepEqual(parsePolicy(v1.policy), { prompt_version: 'v1', descriptor_version: 'v1', call_mode: 'parallel', autonomy: 'confirm' })
  const rows = normalizePolicies([v2, v1])
  assert.equal(rows[0].version, 'V1')
  assert.equal(policiesMatch(rows), true)
  assert.match(summarizePolicies(rows), /No measurable performance difference/)
})

test('reports dynamic regression against baseline', () => {
  const rows = normalizePolicies([v1, { ...v2, final_pass_rate: 0.981 }])
  assert.equal(percentagePointDelta(rows[1], rows[0], 'final_pass_rate').toFixed(1), '-1.9')
  assert.match(summarizePolicies(rows), /Final Pass decreased by 1.9 percentage points/)
  assert.match(summarizePolicies(rows), /Negative Pass was unchanged/)
})
