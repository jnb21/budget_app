// Component tests for the page URLs and the bottom navigation.
// Risk covered: landing on the wrong page, a nav link going nowhere, and the
// month resetting when you switch pages.

import { fireEvent, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { novemberRoutes } from './test/data.js'
import { fakeApi } from './test/fakeApi.js'
import { renderApp } from './test/renderApp.jsx'

test('the first visit shows the welcome screen; "Get started" opens the dashboard', async () => {
  fakeApi(novemberRoutes())
  renderApp('/')

  expect(screen.getByRole('heading', { name: 'Take control of your finances today!' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Get started' }))

  expect(await screen.findByRole('heading', { name: 'Monthly budget' })).toBeTruthy()
})

test('after the welcome screen was seen once, "/" goes straight to the dashboard', () => {
  fakeApi(novemberRoutes())
  localStorage.setItem('budget-app.welcomed', '1')

  renderApp('/')

  expect(screen.getByRole('heading', { name: 'Monthly budget' })).toBeTruthy()
})

test('the bottom nav opens each page and marks the current one', async () => {
  fakeApi(novemberRoutes())
  renderApp('/dashboard')
  const nav = screen.getByRole('navigation', { name: 'Main' })
  expect(nav.querySelector('[aria-current="page"]').getAttribute('aria-label')).toBe('Dashboard')

  fireEvent.click(screen.getByRole('link', { name: 'Budgets' }))

  expect(await screen.findByRole('heading', { name: 'Budgets', level: 1 })).toBeTruthy()
  expect(nav.querySelector('[aria-current="page"]').getAttribute('aria-label')).toBe('Budgets')
})

test('the month picked on one page stays picked on the next', async () => {
  const fetch = fakeApi({ ...novemberRoutes(), 'GET /api/budgets?month=2026-10': [] })
  renderApp('/dashboard')

  fireEvent.click(screen.getByRole('button', { name: 'Previous month' }))
  fireEvent.click(screen.getByRole('link', { name: 'Budgets' }))

  expect(await screen.findByRole('heading', { name: 'Budgets', level: 1 })).toBeTruthy()
  expect(fetch).toHaveBeenCalledWith('/api/budgets?month=2026-10', { method: 'GET' })
})

test('an unknown URL goes back to the start', () => {
  fakeApi(novemberRoutes())
  localStorage.setItem('budget-app.welcomed', '1')

  renderApp('/nope')

  expect(screen.getByRole('heading', { name: 'Monthly budget' })).toBeTruthy()
})
