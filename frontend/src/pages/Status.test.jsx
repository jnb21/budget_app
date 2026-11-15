// Component tests for the status page (/status): a pretend browser (jsdom), a fake fetch,
// no backend. Like the fake repository in the backend tests, the fake fetch
// lets us test every state, including "backend down", in milliseconds.

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import Status from './Status.jsx'

/** A stand-in for the browser's fetch that answers with the given responses, in order. */
function fakeFetch(...answers) {
  const fetch = vi.fn()
  for (const answer of answers) {
    if (answer instanceof Error) fetch.mockRejectedValueOnce(answer)
    else fetch.mockResolvedValueOnce({ status: answer.status, json: async () => answer.body })
  }
  vi.stubGlobal('fetch', fetch)
  return fetch
}

const HEALTHY = { status: 200, body: { status: 'ok', database: 'ok' } }
const DEGRADED = { status: 503, body: { status: 'degraded', database: 'unavailable' } }

afterEach(() => {
  cleanup() // remove the rendered page
  vi.unstubAllGlobals() // put the real fetch back
})

test('shows "Checking…" while waiting, then the healthy message', async () => {
  // Arrange
  fakeFetch(HEALTHY)

  // Act
  render(<Status />)

  // Assert: right away it is checking...
  expect(screen.getByRole('status')).toHaveProperty('textContent', 'Checking…')
  // ...and once the answer arrives (findBy waits for it), it is ok.
  expect(await screen.findByText('Backend and database are up.')).toBeTruthy()
})

test('asks the backend at /health', async () => {
  const fetch = fakeFetch(HEALTHY)

  render(<Status />)
  await screen.findByText('Backend and database are up.')

  expect(fetch).toHaveBeenCalledWith('/health')
})

test('a 503 answer shows that the database is unavailable', async () => {
  fakeFetch(DEGRADED)

  render(<Status />)

  expect(await screen.findByText('The backend is up, but the database is unavailable.')).toBeTruthy()
})

test('no answer at all shows that the backend is unreachable', async () => {
  fakeFetch(new TypeError('Failed to fetch')) // what fetch throws when nothing answers

  render(<Status />)

  expect(await screen.findByText("Can't reach the backend. Is it running?")).toBeTruthy()
})

test('an unexpected status code counts as unreachable', async () => {
  fakeFetch({ status: 502, body: {} }) // what the Vite proxy answers when the backend is stopped

  render(<Status />)

  expect(await screen.findByText("Can't reach the backend. Is it running?")).toBeTruthy()
})

test('"Check again" asks again and shows the new answer', async () => {
  // Arrange: first answer degraded, second answer healthy.
  const fetch = fakeFetch(DEGRADED, HEALTHY)
  render(<Status />)
  await screen.findByText('The backend is up, but the database is unavailable.')

  // Act
  fireEvent.click(screen.getByRole('button', { name: 'Check again' }))

  // Assert
  expect(await screen.findByText('Backend and database are up.')).toBeTruthy()
  expect(fetch).toHaveBeenCalledTimes(2)
})

test('the button is disabled while a check is running', async () => {
  fakeFetch(HEALTHY)

  render(<Status />)

  expect(screen.getByRole('button', { name: 'Check again' })).toHaveProperty('disabled', true)
  await screen.findByText('Backend and database are up.')
  expect(screen.getByRole('button', { name: 'Check again' })).toHaveProperty('disabled', false)
})
