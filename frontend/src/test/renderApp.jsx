import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import App from '../App.jsx'
import MonthProvider from '../MonthProvider.jsx'

/**
 * The whole app at `path`, as a user would open it, but with a pretend URL bar
 * (MemoryRouter) and a fixed month, so tests don't depend on today's date.
 */
export function renderApp(path, { month = '2026-11' } = {}) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <MonthProvider initialMonth={month}>
        <App />
      </MonthProvider>
    </MemoryRouter>,
  )
}
