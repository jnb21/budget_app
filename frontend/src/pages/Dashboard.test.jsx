// Component tests for the dashboard, with a fake fetch and no backend.
// Risk covered: the wrong number in the wrong place (planned vs spent, the
// over-budget warning), and asking the API for the wrong month.

import { fireEvent, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'
import { EMPTY_DASHBOARD, novemberRoutes } from '../test/data.js'
import { fakeApi, reply } from '../test/fakeApi.js'
import { renderApp } from '../test/renderApp.jsx'

test('shows planned expenses, what is left, and how much of the budget is spent', async () => {
  // Arrange
  fakeApi(novemberRoutes())

  // Act
  renderApp('/dashboard')

  // Assert: 2,250.00 planned, 2,019.18 spent -> 230.82 left, 89% (rounded down)
  const hero = await screen.findByRole('region', { name: 'Planned expenses' })
  expect(hero.textContent).toContain('$2,250.00')
  expect(within(hero).getByText('$230.82 left to spend')).toBeTruthy()
  expect(within(hero).getByRole('img', { name: '89% of the budget spent' })).toBeTruthy()
})

test('a card per category says how much of its limit is used, or by how much it is over', async () => {
  fakeApi(novemberRoutes())

  renderApp('/dashboard')

  const cards = await screen.findByRole('region', { name: 'Spending by category' })
  expect(within(cards).getByText('100% of $1,650')).toBeTruthy()
  expect(within(cards).getByText('55% of $550')).toBeTruthy()
  expect(within(cards).getByText('Over by $12.81')).toBeTruthy()
})

test('income is added up per source, and recent spending lists only money spent', async () => {
  fakeApi(novemberRoutes())

  renderApp('/dashboard')

  const income = await screen.findByRole('region', { name: 'My income' })
  expect(income.textContent).toContain('Salary$2,800.00')
  const recent = screen.getByRole('region', { name: 'Spending November' })
  expect(within(recent).getByText('Sushi bar')).toBeTruthy()
  expect(within(recent).getByText('Metro')).toBeTruthy()
  expect(within(recent).queryByText('Salary')).toBeNull()
})

test('spending more than planned shows how much over, with a warning', async () => {
  const routes = novemberRoutes()
  routes['GET /api/dashboard?month=2026-11'].budgeted_cents = 200000 // 2,019.18 spent of 2,000.00
  fakeApi(routes)

  renderApp('/dashboard')

  expect(await screen.findByText('$19.18 over budget')).toBeTruthy()
  expect(screen.getByRole('img', { name: '100% of the budget spent' })).toBeTruthy()
})

test('the month picker loads the previous month', async () => {
  const fetch = fakeApi({
    ...novemberRoutes(),
    'GET /api/dashboard?month=2026-10': EMPTY_DASHBOARD,
    'GET /api/transactions?month=2026-10': [],
  })
  renderApp('/dashboard')
  await screen.findByRole('region', { name: 'Planned expenses' })

  fireEvent.click(screen.getByRole('button', { name: 'Previous month' }))

  expect(await screen.findByText('No income recorded in October yet.')).toBeTruthy()
  expect(screen.getByText('Set your first budget')).toBeTruthy()
  expect(fetch).toHaveBeenCalledWith('/api/dashboard?month=2026-10', { method: 'GET' })
})

test('when loading fails, it says why and "Try again" asks again', async () => {
  const routes = novemberRoutes()
  routes['GET /api/dashboard?month=2026-11'] = reply(503, { detail: 'Database temporarily unavailable, please try again shortly.' })
  fakeApi(routes)
  renderApp('/dashboard')

  expect(await screen.findByText('Database temporarily unavailable, please try again shortly.')).toBeTruthy()

  routes['GET /api/dashboard?month=2026-11'] = novemberRoutes()['GET /api/dashboard?month=2026-11']
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

  expect(await screen.findByRole('region', { name: 'Planned expenses' })).toBeTruthy()
})

test('a stopped backend gets a plain message', async () => {
  fakeApi({ 'GET /api/dashboard?month=2026-11': new TypeError('Failed to fetch') })

  renderApp('/dashboard')

  expect(await screen.findByText("Can't reach the server. Is the backend running?")).toBeTruthy()
  expect(screen.getByRole('link', { name: 'Check backend status' })).toBeTruthy()
})
