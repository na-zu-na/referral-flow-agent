export type Row = Record<string, any>

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message)
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: options?.body ? { 'Content-Type': 'application/json', ...options.headers } : options?.headers,
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload?.ok) {
    throw new ApiError(payload?.error?.code || 'REQUEST_FAILED', payload?.error?.message || 'Request failed.', response.status)
  }
  return payload.data as T
}

function query(values: Record<string, string | number | boolean | null | undefined>) {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value))
  })
  const text = params.toString()
  return text ? `?${text}` : ''
}

export const api = {
  health: () => request<Row>('/api/health'),
  cases: (filters: Row = {}) => request<{ items: Row[]; count: number }>(`/api/cases${query(filters)}`),
  case: (id: string) => request<Row>(`/api/cases/${encodeURIComponent(id)}`),
  createRun: (body: Row) => request<Row>('/api/runs', { method: 'POST', body: JSON.stringify(body) }),
  run: (id: string) => request<Row>(`/api/runs/${encodeURIComponent(id)}`),
  confirm: (id: string, approved: boolean) => request<Row>(`/api/runs/${encodeURIComponent(id)}/confirmation`, {
    method: 'POST', body: JSON.stringify({ approved }),
  }),
  evidence: () => request<Row>('/api/evidence'),
  auditRuns: (filters: Row) => request<{ items: Row[]; count: number }>(`/api/audit/runs${query(filters)}`),
  toolCalls: (runId: string) => request<{ items: Row[]; count: number }>(`/api/audit/tool-calls?run_id=${encodeURIComponent(runId)}`),
}

export const formatNumber = (value: unknown, digits = 2) => {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  return Number.isFinite(number) ? number.toLocaleString('en-US', { maximumFractionDigits: digits }) : String(value)
}

export const formatPercent = (value: unknown) => value === null || value === undefined ? '—' : `${(Number(value) * 100).toFixed(1)}%`
export const formatCost = (value: unknown) => value === null || value === undefined ? '—' : `$${Number(value).toFixed(6)}`
