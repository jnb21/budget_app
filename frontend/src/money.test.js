// Unit tests for money formatting and parsing: plain functions, no page.
// Risk covered: a wrong amount on screen, or a typed "12.5" saved as $1.25.

import { expect, test } from 'vitest'
import { centsToInput, formatMoney, formatMoneyShort, parseAmount, splitCents } from './money.js'

test('splits cents into grouped dollars and two-digit cents', () => {
  expect(splitCents(147500)).toEqual({ negative: false, dollars: '1,475', cents: '00' })
  expect(splitCents(-5)).toEqual({ negative: true, dollars: '0', cents: '05' })
})

test('formats amounts, with a + only when asked', () => {
  expect(formatMoney(5499)).toBe('$54.99')
  expect(formatMoney(-5499)).toBe('−$54.99')
  expect(formatMoney(5499, { plus: true })).toBe('+$54.99')
  expect(formatMoney(123456789)).toBe('$1,234,567.89')
})

test('short format drops ".00" but keeps real cents', () => {
  expect(formatMoneyShort(3200)).toBe('$32')
  expect(formatMoneyShort(3250)).toBe('$32.50')
})

test('an amount goes back into a form field without commas', () => {
  expect(centsToInput(123456)).toBe('1234.56')
  expect(centsToInput(500)).toBe('5.00')
})

test.each([
  ['12', 1200],
  ['12.5', 1250],
  ['12.50', 1250],
  ['0.99', 99],
  ['.99', 99],
  ['1,234.56', 123456],
  ['$ 40', 4000],
  ['0', 0],
])('reads %j as %i cents', (text, cents) => {
  expect(parseAmount(text)).toBe(cents)
})

test.each([
  '', '.', 'abc', '12.345', '-5', '1.2.3',
  '12,50',    // a French decimal comma: must NOT be read as $1,250.00
  '1,23',     // a comma that isn't in a thousands position
  '1234,567', // same
])('rejects %j', (text) => {
  expect(parseAmount(text)).toBeNull()
})
