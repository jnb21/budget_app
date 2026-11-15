// Every call to the backend goes through this file, so components never deal
// with URLs or HTTP status codes themselves (like routers vs. services).
// Amounts are integer cents; months are "2026-11".

/** A failed API call. `message` is ready to show to the user. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status // 0 = no answer at all
  }
}

/** The backend's {"detail": ...} as one sentence. */
function messageFrom(body, status) {
  const detail = body?.detail
  if (typeof detail === 'string') return capitalize(detail)
  // FastAPI's own validation errors are a list: [{ msg: "...", loc: [...] }, ...]
  if (Array.isArray(detail) && detail[0]?.msg) return capitalize(detail[0].msg)
  if (status === 503) return 'The database is unavailable. Try again in a moment.'
  return `Something went wrong (error ${status}).`
}

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1)

async function request(method, path, body) {
  const options = { method }
  if (body !== undefined) {
    options.headers = { 'Content-Type': 'application/json' }
    options.body = JSON.stringify(body)
  }
  let response
  try {
    response = await fetch(path, options)
  } catch {
    throw new ApiError("Can't reach the server. Is the backend running?", 0)
  }
  if (response.status === 204) return null // deleted: no body
  const data = await response.json().catch(() => null)
  if (response.status < 200 || response.status >= 300) {
    // 502/504 come from the Vite proxy when the backend is stopped.
    if (response.status === 502 || response.status === 504) {
      throw new ApiError("Can't reach the server. Is the backend running?", response.status)
    }
    throw new ApiError(messageFrom(data, response.status), response.status)
  }
  return data
}

const query = (month) => `?month=${encodeURIComponent(month)}`

/**
 * Ask the backend for its health.
 * Resolves to { status: "ok" | "degraded", database: "ok" | "unavailable" }.
 * Throws if the backend can't be reached or answers something unexpected.
 */
export async function getHealth() {
  const response = await fetch('/health') // throws by itself if there is no network at all
  // 200 = healthy, 503 = up but degraded. Both carry the JSON body we expect.
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`Unexpected status ${response.status}`)
  }
  return response.json()
}

// Dashboard: { month, income_cents, spent_cents, net_cents, budgeted_cents, categories: [...] }
export const getDashboard = (month) => request('GET', `/api/dashboard${query(month)}`)

// Categories: [{ id, name, is_default }]
export const getCategories = () => request('GET', '/api/categories')
export const createCategory = (name) => request('POST', '/api/categories', { name })

// Transactions: [{ id, posted_date, amount_cents, description, category_id, category_name, category_source }]
export const getTransactions = (month) => request('GET', `/api/transactions${query(month)}`)
/** draft: { posted_date: "2026-11-14", amount_cents, description, category_id | null } */
export const createTransaction = (draft) => request('POST', '/api/transactions', draft)
export const updateTransaction = (id, draft) => request('PUT', `/api/transactions/${id}`, draft)
export const deleteTransaction = (id) => request('DELETE', `/api/transactions/${id}`)

// Budgets: [{ id, category_id, category_name, month: "2026-11-01", limit_cents }]
export const getBudgets = (month) => request('GET', `/api/budgets${query(month)}`)
export const setBudget = (categoryId, month, limitCents) =>
  request('PUT', '/api/budgets', { category_id: categoryId, month, limit_cents: limitCents })
export const deleteBudget = (id) => request('DELETE', `/api/budgets/${id}`)
