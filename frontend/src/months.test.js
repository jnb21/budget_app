// Unit tests for month and date helpers.
// Risk covered: December -> January going wrong, or a date shown a day early
// because it was read as UTC midnight.

import { expect, test } from 'vitest'
import { currentMonth, defaultDayFor, formatDay, monthLabel, shiftMonth } from './months.js'

test('the current month comes from the local date', () => {
  expect(currentMonth(new Date(2026, 10, 30, 23, 59))).toBe('2026-11')
})

test('moving across a year boundary', () => {
  expect(shiftMonth('2026-01', -1)).toBe('2025-12')
  expect(shiftMonth('2025-12', 1)).toBe('2026-01')
  expect(shiftMonth('2026-11', -13)).toBe('2025-10')
})

test('labels', () => {
  expect(monthLabel('2026-11')).toBe('November 2026')
  expect(formatDay('2026-11-14')).toBe('Sat, Nov 14') // the local day, never the day before
})

test('a new transaction starts today in the current month, else on the 1st', () => {
  const today = new Date(2026, 10, 15)
  expect(defaultDayFor('2026-11', today)).toBe('2026-11-15')
  expect(defaultDayFor('2026-10', today)).toBe('2026-10-01')
})
