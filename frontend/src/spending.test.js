// Unit tests for "spent so far": it must count like the backend's dashboard.
// Risk covered: the month-over-month chip disagreeing with the dashboard.

import { expect, test } from 'vitest'
import { spentThrough } from './spending.js'

const t = (day, cents, categoryId) => ({ posted_date: `2026-11-${day}`, amount_cents: cents, category_id: categoryId })

test('adds up spending through the given day only', () => {
  const transactions = [t('03', -1000, 1), t('10', -500, 2), t('20', -9999, 1)]
  expect(spentThrough(transactions, 10)).toBe(1500)
  expect(spentThrough(transactions, 31)).toBe(11499)
})

test('a refund lowers its own category, and income is not spending', () => {
  const transactions = [t('01', -5000, 8), t('02', 2500, 8), t('15', 280000, 10)]
  expect(spentThrough(transactions, 31)).toBe(2500)
})

test('uncategorized transactions count as one category', () => {
  expect(spentThrough([t('01', -700, null), t('02', -300, null)], 31)).toBe(1000)
})
