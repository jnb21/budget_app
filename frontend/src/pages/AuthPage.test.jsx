// Component tests for logging in, signing up, and being sent to the login page.
// Risk covered: seeing data without a login, a login that doesn't stick, a
// backend refusal not shown, and an expired session leaving a broken page.

import { fireEvent, screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { novemberRoutes } from '../test/data.js'
import { fakeApi, reply, sent } from '../test/fakeApi.js'
import { ALICE, renderApp } from '../test/renderApp.jsx'

const type = (label, value) => fireEvent.change(screen.getByLabelText(label), { target: { value } })

test('without a login, a page of data sends you to the login page', async () => {
  fakeApi(novemberRoutes())

  renderApp('/dashboard', { user: null })

  expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
})

test('logging in sends the email and password, then opens the page you wanted', async () => {
  const fetch = fakeApi({ ...novemberRoutes(), 'POST /api/auth/login': ALICE })
  renderApp('/budgets', { user: null })
  await screen.findByRole('heading', { name: 'Welcome back' })

  type('Email', '  alice@example.com ')
  type('Password', 'correct horse battery')
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

  expect(await screen.findByRole('heading', { name: 'Budgets', level: 1 })).toBeTruthy()
  expect(sent(fetch, 'POST /api/auth/login')).toEqual([{ email: 'alice@example.com', password: 'correct horse battery' }])
})

test.each([
  [401, 'wrong email or password', 'Wrong email or password'],
  [429, 'too many failed attempts; try again in 15 minutes', 'Too many failed attempts; try again in 15 minutes'],
])('a %i from the backend is shown and you stay on the login page', async (status, detail, shown) => {
  fakeApi({ 'POST /api/auth/login': reply(status, { detail }) })
  renderApp('/login', { user: null })

  type('Email', 'alice@example.com')
  type('Password', 'not the password')
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

  expect((await screen.findByRole('alert')).textContent).toBe(shown)
  expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeTruthy()
})

test('sign up shows each password rule live as you type', async () => {
  fakeApi({})
  renderApp('/signup', { user: null })
  const rules = () => screen.getByRole('list', { name: 'Password rules' })

  type('Email', 'alice@example.com')
  type('Password', 'abcdefghijk') // long enough, letters only

  expect(within(rules()).getByText('10 to 128 characters').closest('li').className).toContain('rule-ok')
  expect(within(rules()).getByText('At least one number, symbol or space').closest('li').className).toContain('rule-bad')

  type('Password', 'abcdefghijk 7')
  expect(within(rules()).getByText('At least one number, symbol or space').closest('li').className).toContain('rule-ok')
})

test('a password that breaks a rule is refused before calling the backend', async () => {
  const fetch = fakeApi({})
  renderApp('/signup', { user: null })

  type('Email', 'alice@example.com')
  type('Password', 'short')
  type('Confirm password', 'short')
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

  expect((await screen.findByRole('alert')).textContent).toContain('10 to 128 characters')
  expect(fetch).not.toHaveBeenCalled()
})

test('the two passwords must match', async () => {
  const fetch = fakeApi({})
  renderApp('/signup', { user: null })

  type('Email', 'alice@example.com')
  type('Password', 'correct horse battery')
  type('Confirm password', 'correct horse batery')

  expect(screen.getByText("Passwords don't match")).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
  expect((await screen.findByRole('alert')).textContent).toBe("The two passwords don't match.")
  expect(fetch).not.toHaveBeenCalled()

  type('Confirm password', 'correct horse battery')
  expect(screen.getByText('Passwords match')).toBeTruthy()
})

test('the eye button shows and hides the password', () => {
  fakeApi({})
  renderApp('/signup', { user: null })
  const field = screen.getByLabelText('Password')
  expect(field.type).toBe('password')

  fireEvent.click(screen.getByRole('button', { name: 'Show password' }))
  expect(field.type).toBe('text')

  fireEvent.click(screen.getByRole('button', { name: 'Hide password' }))
  expect(field.type).toBe('password')
})

test('signing up logs you in and opens the dashboard', async () => {
  const fetch = fakeApi({ ...novemberRoutes(), 'POST /api/auth/signup': reply(201, ALICE) })
  renderApp('/signup', { user: null })

  type('Email', 'alice@example.com')
  type('Password', 'correct horse battery')
  type('Confirm password', 'correct horse battery')
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

  expect(await screen.findByRole('heading', { name: 'Monthly budget' })).toBeTruthy()
  expect(sent(fetch, 'POST /api/auth/signup')).toHaveLength(1)
})

test('at startup the app asks who is logged in', async () => {
  const fetch = fakeApi({ ...novemberRoutes(), 'GET /api/auth/me': ALICE })

  renderApp('/dashboard', { askBackend: true })

  expect(await screen.findByRole('heading', { name: 'Monthly budget' })).toBeTruthy()
  expect(fetch).toHaveBeenCalledWith('/api/auth/me', { method: 'GET' })
})

test('at startup a 401 means the login page', async () => {
  fakeApi({ 'GET /api/auth/me': reply(401, { detail: 'please log in' }) })

  renderApp('/dashboard', { askBackend: true })

  expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
})

test('at startup an unreachable backend says so, with a way to try again', async () => {
  fakeApi({ 'GET /api/auth/me': new TypeError('Failed to fetch') })

  renderApp('/dashboard', { askBackend: true })

  expect((await screen.findByRole('alert')).textContent).toContain("Can't reach the server")
  expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy()
})

test('when the session expires mid-use, the login page appears', async () => {
  fakeApi({ ...novemberRoutes(), 'GET /api/dashboard?month=2026-11': reply(401, { detail: 'please log in' }) })

  renderApp('/dashboard')

  expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
})

test('logging out calls the backend and shows the login page', async () => {
  const fetch = fakeApi({ ...novemberRoutes(), 'POST /api/auth/logout': reply(204) })
  renderApp('/account')

  // Two "Log out" buttons exist (sidebar and this page): use the one on the page.
  fireEvent.click(within(await screen.findByRole('main')).getByRole('button', { name: 'Log out' }))

  expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeTruthy()
  await vi.waitFor(() => expect(sent(fetch, 'POST /api/auth/logout')).toHaveLength(1))
})

test('the nav shows who is logged in', async () => {
  fakeApi(novemberRoutes())

  renderApp('/dashboard')

  expect(await screen.findByText('alice@example.com')).toBeTruthy()
})
