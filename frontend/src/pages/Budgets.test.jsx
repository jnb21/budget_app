// Component tests for the budgets page, with a fake fetch.
// Risk covered: a limit saved for the wrong category or month, or in dollars
// instead of cents; removing the wrong budget; Income offered as a spending limit.

import { fireEvent, screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { novemberRoutes } from '../test/data.js'
import { fakeApi, reply, sent } from '../test/fakeApi.js'
import { renderApp } from '../test/renderApp.jsx'

async function openPage(routes = novemberRoutes()) {
  const fetch = fakeApi(routes)
  renderApp('/budgets')
  await screen.findByRole('region', { name: 'Planned for November' })
  return fetch
}

const dialog = () => screen.getByRole('dialog')

test('lists categories with a limit (spent of limit) and without one; Income is not a spending category', async () => {
  await openPage()

  expect(screen.getByRole('region', { name: 'Planned for November' }).textContent).toContain('$2,250.00')
  const withLimit = screen.getByRole('region', { name: 'With a limit' })
  expect(within(withLimit).getByRole('button', { name: 'Groceries: $306.37 of $550.00 spent, 55%. Edit limit' })).toBeTruthy()
  expect(within(withLimit).getByRole('button', { name: 'Dining out: $62.81 of $50.00 spent, 125%, over by $12.81. Edit limit' })).toBeTruthy()
  const withoutLimit = screen.getByRole('region', { name: 'No limit yet' })
  expect(within(withoutLimit).getByRole('button', { name: /^Health:/ })).toBeTruthy()
  expect(screen.queryByRole('button', { name: /^Income:/ })).toBeNull()
})

test('setting a limit sends the category, the month and the limit in cents', async () => {
  const routes = novemberRoutes()
  routes['PUT /api/budgets'] = (body) => ({ id: 20, category_name: 'Health', month: '2026-11-01', ...body })
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: /^Health:/ }))
  expect(screen.getByRole('dialog', { name: 'Health limit for November' })).toBeTruthy()
  fireEvent.change(within(dialog()).getByRole('textbox', { name: 'Monthly limit' }), { target: { value: '80' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Set limit' }))

  await vi.waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  expect(sent(fetch, 'PUT /api/budgets')).toEqual([{ category_id: 7, month: '2026-11', limit_cents: 8000 }])
})

test('an existing limit opens filled in and can be changed', async () => {
  const routes = novemberRoutes()
  routes['PUT /api/budgets'] = (body) => ({ id: 8, category_name: 'Groceries', month: '2026-11-01', ...body })
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: /^Groceries:/ }))
  const input = within(dialog()).getByRole('textbox', { name: 'Monthly limit' })
  expect(input.value).toBe('550.00')
  fireEvent.change(input, { target: { value: '600' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Save limit' }))

  await vi.waitFor(() => expect(sent(fetch, 'PUT /api/budgets')).toEqual([{ category_id: 1, month: '2026-11', limit_cents: 60000 }]))
})

test('"Remove limit" deletes that budget', async () => {
  const routes = novemberRoutes()
  routes['DELETE /api/budgets/9'] = reply(204)
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: /^Dining out:/ }))
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Remove limit' }))

  await vi.waitFor(() => expect(sent(fetch, 'DELETE /api/budgets/9')).toHaveLength(1))
})

test('a limit of zero is refused before anything is sent', async () => {
  const fetch = await openPage()

  fireEvent.click(screen.getByRole('button', { name: /^Health:/ }))
  fireEvent.change(within(dialog()).getByRole('textbox', { name: 'Monthly limit' }), { target: { value: '0' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Set limit' }))

  expect(within(dialog()).getByRole('alert').textContent).toBe('Enter a limit, like 150.')
  expect(sent(fetch, 'PUT /api/budgets')).toEqual([])
})

test('creating a category that already exists shows why', async () => {
  const routes = novemberRoutes()
  routes['POST /api/categories'] = reply(409, { detail: 'a category with that name already exists' })
  const fetch = await openPage(routes)

  fireEvent.click(screen.getByRole('button', { name: 'New category' }))
  fireEvent.change(within(dialog()).getByRole('textbox', { name: 'Name' }), { target: { value: 'Health' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Create category' }))

  expect(await within(dialog()).findByText('A category with that name already exists')).toBeTruthy()
  expect(sent(fetch, 'POST /api/categories')).toEqual([{ name: 'Health' }])
})
