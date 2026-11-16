// Component tests for the account page: your categories, your data, deleting.
// Risk covered: renaming or deleting the wrong category, deleting the account
// without the password check, and the export not reaching the user.

import { fireEvent, screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { CATEGORIES } from '../test/data.js'
import { fakeApi, reply, sent } from '../test/fakeApi.js'
import { renderApp } from '../test/renderApp.jsx'

const PETS = { id: 50, name: 'Pets', is_default: false }
const dialog = () => screen.getByRole('dialog')

function setup(extra = {}) {
  const fetch = fakeApi({ 'GET /api/categories': [...CATEGORIES, PETS], ...extra })
  renderApp('/account')
  return fetch
}

test('shows who you are and only your own categories', async () => {
  setup()

  expect(await screen.findByText('Pets')).toBeTruthy()
  expect(screen.getAllByText('alice@example.com').length).toBeGreaterThan(0)
  expect(screen.queryByRole('button', { name: 'Rename Groceries' })).toBeNull() // defaults can't be changed
})

test('renaming a category sends the new name', async () => {
  const fetch = setup({ 'PUT /api/categories/50': { ...PETS, name: 'Pet care' } })

  fireEvent.click(await screen.findByRole('button', { name: 'Rename Pets' }))
  fireEvent.change(within(dialog()).getByLabelText('Name'), { target: { value: 'Pet care' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Save' }))

  await vi.waitFor(() => expect(sent(fetch, 'PUT /api/categories/50')).toEqual([{ name: 'Pet care' }]))
})

test('a duplicate name is explained', async () => {
  setup({ 'PUT /api/categories/50': reply(409, { detail: "a category named 'Groceries' already exists" }) })

  fireEvent.click(await screen.findByRole('button', { name: 'Rename Pets' }))
  fireEvent.change(within(dialog()).getByLabelText('Name'), { target: { value: 'Groceries' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Save' }))

  expect((await within(dialog()).findByRole('alert')).textContent).toBe("A category named 'Groceries' already exists")
})

test('deleting a category asks first, then deletes that one', async () => {
  const fetch = setup({ 'DELETE /api/categories/50': reply(204) })

  fireEvent.click(await screen.findByRole('button', { name: 'Delete Pets' }))
  expect(within(dialog()).getByText(/will become/).textContent).toContain('Uncategorized')
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Delete category' }))

  await vi.waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/categories/50', { method: 'DELETE' }))
})

test('deleting the account needs the password', async () => {
  const fetch = setup({ 'POST /api/account/delete': reply(422, { detail: 'wrong password' }) })

  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }))
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Delete my account' }))
  expect(within(dialog()).getByRole('alert').textContent).toBe('Enter your password to confirm.')
  expect(sent(fetch, 'POST /api/account/delete')).toHaveLength(0)

  fireEvent.change(within(dialog()).getByLabelText('Password'), { target: { value: 'not the password' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Delete my account' }))

  expect((await within(dialog()).findByRole('alert')).textContent).toBe('Wrong password')
})

test('after deleting the account you are logged out', async () => {
  const fetch = setup({ 'POST /api/account/delete': reply(204) })

  fireEvent.click(await screen.findByRole('button', { name: 'Delete account' }))
  fireEvent.change(within(dialog()).getByLabelText('Password'), { target: { value: 'correct horse battery' } })
  fireEvent.click(within(dialog()).getByRole('button', { name: 'Delete my account' }))

  expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
  expect(sent(fetch, 'POST /api/account/delete')).toEqual([{ password: 'correct horse battery' }])
})

test('download gets your data and saves it as a JSON file', async () => {
  const fetch = setup({ 'GET /api/account/export': { account: { email: 'alice@example.com' }, transactions: [] } })
  const createObjectURL = vi.fn(() => 'blob:fake')
  vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL: vi.fn() })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

  fireEvent.click(await screen.findByRole('button', { name: /Download/ }))

  await vi.waitFor(() => expect(click).toHaveBeenCalled())
  expect(fetch).toHaveBeenCalledWith('/api/account/export', { method: 'GET' })
  expect(createObjectURL.mock.calls[0][0].type).toBe('application/json')
  click.mockRestore()
})
