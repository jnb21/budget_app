import { useEffect, useState } from 'react'
import { getHealth } from '../api.js'

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

/** Is the backend up? Linked from every "couldn't load" message. */
export default function Status() {
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
    <main className="page">
      <header className="page-header">
        <h1 className="page-title">Status</h1>
      </header>
      <section className={`card status status-${status}`}>
        <h2 className="section-title">Backend status</h2>
        {/* role="status" makes screen readers announce the message when it changes */}
        <p role="status">{MESSAGES[status]}</p>
        <button type="button" className="button" onClick={checkAgain} disabled={status === 'checking'}>
          Check again
        </button>
      </section>
    </main>
  )
}
