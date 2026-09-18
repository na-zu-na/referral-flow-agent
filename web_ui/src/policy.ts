export type PolicyRow = Record<string, any> & { config: Record<string, string>; version: string }

export const POLICY_METRICS = [
  { key: 'final_pass_rate', label: 'Final Pass' },
  { key: 'negative_final_pass_rate', label: 'Negative Pass' },
  { key: 'diagnostic_clean_rate', label: 'Diagnostic Clean' },
] as const

export function parsePolicy(value = ''): Record<string, string> {
  return Object.fromEntries(value.split('|').map((part) => part.split('=', 2)).filter((pair) => pair.length === 2))
}

export function normalizePolicies(rows: Record<string, any>[]): PolicyRow[] {
  return rows.map((row): PolicyRow => {
    const config = parsePolicy(row.policy)
    return { ...row, config, version: String(config.prompt_version || 'policy').toUpperCase() }
  }).sort((a, b) => a.version.localeCompare(b.version, undefined, { numeric: true }))
}

export const percentagePointDelta = (row: PolicyRow | undefined, baseline: PolicyRow | undefined, key: string) =>
  (Number(row?.[key]) - Number(baseline?.[key])) * 100

export function formatDelta(value: number, prefix = true): string {
  const normalized = Math.abs(value) < 0.05 ? 0 : value
  return `${prefix ? 'Δ ' : ''}${normalized > 0 ? '+' : ''}${normalized.toFixed(1)}%`
}

export function policiesMatch(rows: PolicyRow[]): boolean {
  const baseline = rows[0]
  return rows.length > 1 && POLICY_METRICS.every(({ key }) =>
    rows.every((row) => Math.abs(Number(row[key]) - Number(baseline[key])) < 0.0005),
  )
}

export function summarizePolicies(rows: PolicyRow[]): string {
  const baseline = rows[0]
  const current = rows.at(-1)
  if (!baseline || !current) return ''
  if (policiesMatch(rows)) {
    const rate = `${(Number(current.final_pass_rate) * 100).toFixed(1)}%`
    return `${baseline.version} and ${current.version} both achieved ${rate} for Final Pass, Negative Pass, and Diagnostic Clean across ${current.runs} runs. No measurable performance difference was observed.`
  }
  const changes = POLICY_METRICS.map(({ key, label }) => {
    const delta = percentagePointDelta(current, baseline, key)
    return Math.abs(delta) < 0.05
      ? `${label} was unchanged`
      : `${label} ${delta > 0 ? 'increased' : 'decreased'} by ${Math.abs(delta).toFixed(1)} percentage points`
  })
  return `${current.version} compared with ${baseline.version}: ${changes.join('; ')}.`
}
