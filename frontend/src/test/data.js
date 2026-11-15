// Hand-made API answers for November and October 2026, consistent with each other:
// the dashboard's numbers are what the backend would compute from TRANSACTIONS
// and BUDGETS. Tests copy them (structuredClone) before changing anything.

export const CATEGORIES = [
  { id: 1, name: 'Groceries', is_default: true },
  { id: 2, name: 'Rent', is_default: true },
  { id: 5, name: 'Dining out', is_default: true },
  { id: 7, name: 'Health', is_default: true },
  { id: 10, name: 'Income', is_default: true },
]

export const TRANSACTIONS = [
  { id: 101, posted_date: '2026-11-14', amount_cents: -6281, description: 'Sushi bar', category_id: 5, category_name: 'Dining out', category_source: 'user' },
  { id: 102, posted_date: '2026-11-14', amount_cents: 280000, description: 'Salary', category_id: 10, category_name: 'Income', category_source: 'user' },
  { id: 103, posted_date: '2026-11-12', amount_cents: -30637, description: 'Metro', category_id: 1, category_name: 'Groceries', category_source: 'user' },
  { id: 104, posted_date: '2026-11-01', amount_cents: -165000, description: 'Rent', category_id: 2, category_name: 'Rent', category_source: 'user' },
]

export const BUDGETS = [
  { id: 7, category_id: 2, category_name: 'Rent', month: '2026-11-01', limit_cents: 165000 },
  { id: 8, category_id: 1, category_name: 'Groceries', month: '2026-11-01', limit_cents: 55000 },
  { id: 9, category_id: 5, category_name: 'Dining out', month: '2026-11-01', limit_cents: 5000 },
]

// Spent 2,019.18 of 2,250.00 planned; Dining out is over its 50.00 by 12.81.
export const DASHBOARD = {
  month: '2026-11',
  income_cents: 280000,
  spent_cents: 201918,
  net_cents: 78082,
  budgeted_cents: 225000,
  categories: [
    { category_id: 2, category_name: 'Rent', spent_cents: 165000, limit_cents: 165000, remaining_cents: 0, percent_used: 100, status: 'near' },
    { category_id: 1, category_name: 'Groceries', spent_cents: 30637, limit_cents: 55000, remaining_cents: 24363, percent_used: 55, status: 'ok' },
    { category_id: 5, category_name: 'Dining out', spent_cents: 6281, limit_cents: 5000, remaining_cents: -1281, percent_used: 125, status: 'over' },
  ],
}

// October: 2,250.00 spent in all, 1,650.00 of it by the 15th.
export const OCTOBER_TRANSACTIONS = [
  { id: 91, posted_date: '2026-10-20', amount_cents: -60000, description: 'Costco', category_id: 1, category_name: 'Groceries', category_source: 'user' },
  { id: 90, posted_date: '2026-10-01', amount_cents: -165000, description: 'Rent', category_id: 2, category_name: 'Rent', category_source: 'user' },
]

export const EMPTY_DASHBOARD = {
  month: '2026-10',
  income_cents: 0,
  spent_cents: 0,
  net_cents: 0,
  budgeted_cents: 0,
  categories: [],
}

/** Everything the pages ask for in November, as fakeApi routes (fresh copies each call). */
export function novemberRoutes() {
  return structuredClone({
    'GET /api/categories': CATEGORIES,
    'GET /api/dashboard?month=2026-11': DASHBOARD,
    'GET /api/transactions?month=2026-11': TRANSACTIONS,
    'GET /api/transactions?month=2026-10': OCTOBER_TRANSACTIONS,
    'GET /api/budgets?month=2026-11': BUDGETS,
  })
}
