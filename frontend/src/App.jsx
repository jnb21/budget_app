import { useEffect, useState } from 'react'
import { getHealth } from './api.js'
import './App.css'

const MESSAGES = {
  checking: 'Checking…',
  ok: 'Backend and database are up.',
  degraded: 'The backend is up, but the database is unavailable.',
  unreachable: "Can't reach the backend. Is it running?",
}

// Turns the API result (or failure) into one of the four states above.
async function loadStatus() {
  try {
    const health = await getHealth()
    return health.status === 'ok' ? 'ok' : 'degraded'
  } catch {
    return 'unreachable'
  }
}

export default function App() {
  const [status, setStatus] = useState('checking')

  // Check once when the page opens.
  useEffect(() => {
    let cancelled = false
    loadStatus().then((result) => {
      if (!cancelled) setStatus(result) // ignore the answer if the page is already gone
    })
    return () => {
      cancelled = true
    }
  }, [])

  function checkAgain() {
    setStatus('checking')
    loadStatus().then(setStatus)
  }

  return (
    <main>
      <h1>Budget App</h1>
      <section className={`status status-${status}`}>
        <h2>Backend status</h2>
        {/* role="status" makes screen readers announce the message when it changes */}
        <p role="status">{MESSAGES[status]}</p>
        <button type="button" onClick={checkAgain} disabled={status === 'checking'}>
          Check again
        </button>
      </section>
    </main>
  )
}
