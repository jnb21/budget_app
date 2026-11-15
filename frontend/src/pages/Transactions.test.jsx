// Component tests for the transactions page and its add/edit form, with a fake fetch.
// Risk covered: an expense saved as income (wrong sign), dollars saved as cents,
// a server error swallowed, editing or deleting the wrong transaction.

import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { novemberRoutes, TRANSACTIONS } from '../test/data.js'
import { fakeApi, reply, sent } from '../test/fakeApi.js'
import { renderApp } from '../test/renderApp.jsx'

beforeEach(() => {
  // "Today" is Dec 20, 2026, so November is a finished month. Only Date is
  // faked: real timers keep the async waiting in findBy working.
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 11, 20))
})

async function openPage(routes = novemberRoutes()) {
  const fetch = fakeApi(routes)
  renderApp('/transactions')
  await screen.findByRole('region', { name: 'Net for November' })
  return fetch
}

const dialog = () => screen.getByRole('dialog')
const field = (name, role = 'textbox') => within(dialog()).getByRole(role, { name })

test('shows the net, money in and out, and the transactions grouped by day', async () => {
  await openPage()

  const net = screen.getByRole('region', { name: 'Net for November' })
  expect(net.textContent).toContain('$780.82')
  expect(net.textContent).toContain('+$2,800.00')
  expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual(
    expect.arrayContaining(['Sat, Nov 14', 'Thu, Nov 12', 'Sun, Nov 1']),
  )
  const nov14 = screen.getByRole('region', { name: 'Sat, Nov 14' })
  expect(within(nov14).getAllByRole('listitem')).toHaveLength(2)
})

test('compares with the whole previous month once a month is over', async () => {
  await openPage()

  // November 2,019.18 vs October 2,250.00
  expect(screen.getByText('10% less spent than October')).toBeTruthy()
})

test('during the month, compares with the same days of the previous month', async () => {
  vi.setSystemTime(new Date(2026, 10, 15))

  await openPage()

  // November 1–15: 2,019.18 vs October 1–15: 1,650.00
  expect(screen.getByText('22% more spent than Oct 1–15')).toBeTruthy()
})

test('adding an expense sends a negative amount in cents, then shows the new list', async () => {
  const routes = novemberRoutes()
  const created = { id: 200, posted_date: '2026-11-01', amount_cents: -1250, description: 'Coffee', category_id: 5, category_name: 'Dining out', category_source: 'user' }
  routes['POST /api/transactions'] = reply(201, created)
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: 'New transaction' }))
  fireEvent.change(field('Amount'), { target: { value: '12.5' } })
  fireEvent.change(field('Description'), { target: { value: '  Coffee ' } })
  fireEvent.change(field('Category', 'combobox'), { target: { value: '5' } })
  routes['GET /api/transactions?month=2026-11'] = [created, ...TRANSACTIONS] // what the reload will get
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Add transaction' }))

  expect(await screen.findByText('Coffee')).toBeTruthy()
  expect(screen.queryByRole('dialog')).toBeNull()
  expect(sent(fetch, 'POST /api/transactions')).toEqual([
    { posted_date: '2026-11-01', amount_cents: -1250, description: 'Coffee', category_id: 5 },
  ])
})

test('switching to income makes the amount positive and picks the Income category', async () => {
  const routes = novemberRoutes()
  routes['POST /api/transactions'] = reply(201, {})
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: 'New transaction' }))
  fireEvent.click(within(dialog()).getByRole('radio', { name: 'Income' }))
  fireEvent.change(field('Amount'), { target: { value: '100' } })
  fireEvent.change(field('Description'), { target: { value: 'Gift' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Add transaction' }))

  await vi.waitFor(() => expect(sent(fetch, 'POST /api/transactions')).toHaveLength(1))
  expect(sent(fetch, 'POST /api/transactions')[0]).toMatchObject({ amount_cents: 10000, category_id: 10 })
})

test('an amount that is not a number is caught before anything is sent', async () => {
  const fetch = await openPage()

  fireEvent.click(screen.getByRole('button', { name: 'New transaction' }))
  fireEvent.change(field('Amount'), { target: { value: 'twelve' } })
  fireEvent.change(field('Description'), { target: { value: 'Coffee' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Add transaction' }))

  expect(within(dialog()).getByRole('alert').textContent).toBe('Enter an amount, like 12.50.')
  expect(sent(fetch, 'POST /api/transactions')).toEqual([])
})

test("the backend's reason for refusing is shown, and the form stays open", async () => {
  const routes = novemberRoutes()
  routes['POST /api/transactions'] = reply(422, { detail: 'amount is larger than $1,000,000' })
  await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: 'New transaction' }))
  fireEvent.change(field('Amount'), { target: { value: '2000000' } })
  fireEvent.change(field('Description'), { target: { value: 'Yacht' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Add transaction' }))

  expect(await within(dialog()).findByText('Amount is larger than $1,000,000')).toBeTruthy()
})

test('tapping a transaction opens it filled in, and saving sends a PUT for that one', async () => {
  const routes = novemberRoutes()
  routes['PUT /api/transactions/103'] = (body) => ({ ...TRANSACTIONS[2], ...body })
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: /^Metro/ }))
  expect(field('Amount').value).toBe('306.37')
  expect(field('Description').value).toBe('Metro')
  fireEvent.change(field('Amount'), { target: { value: '310' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Save changes' }))

  await vi.waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  expect(sent(fetch, 'PUT /api/transactions/103')).toEqual([
    { posted_date: '2026-11-12', amount_cents: -31000, description: 'Metro', category_id: 1 },
  ])
})

test('deleting asks for a second tap, then sends DELETE', async () => {
  const routes = novemberRoutes()
  routes['DELETE /api/transactions/103'] = reply(204)
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: /^Metro/ }))
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Delete' }))
  expect(sent(fetch, 'DELETE /api/transactions/103')).toEqual([]) // not yet
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Tap again to delete' }))

  await vi.waitFor(() => expect(sent(fetch, 'DELETE /api/transactions/103')).toHaveLength(1))
})

test('Escape closes the form without saving', async () => {
  await openPage()

  fireEvent.click(screen.getByRole('button', { name: 'New transaction' }))
  fireEvent.keyDown(document, { key: 'Escape' })

  expect(screen.queryByRole('dialog')).toBeNull()
})

test('an empty month says so and offers to add one', async () => {
  const routes = novemberRoutes()
  routes['GET /api/transactions?month=2026-11'] = []
  await openPage(routes)

  expect(screen.getByText('No transactions in November yet.')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Add a transaction' }))
  expect(screen.getByRole('dialog', { name: 'New transaction' })).toBeTruthy()
})
