import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import App from '../App.jsx'
import AuthProvider from '../AuthProvider.jsx'
import MonthProvider from '../MonthProvider.jsx'

export const ALICE = { id: 1, email: 'alice@example.com' }

/**
 * The whole app at `path`, as a user would open it, but with a pretend URL bar
 * (MemoryRouter) and a fixed month, so tests don't depend on today's date.
 *
 * `user`: who is logged in (Alice by default), or null for nobody.
 * `askBackend: true`: start unknown and ask GET /api/auth/me, like the real
 * browser does. (Passing user: undefined wouldn't work: JavaScript would use
 * the default, Alice.)
 */
export function renderApp(path, { month = '2026-11', user = ALICE, askBackend = false } = {}) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initialUser={askBackend ? undefined : user}>
        <MonthProvider initialMonth={month}>
          <App />
        </MonthProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}
