import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Runs `load()` (an async function that calls the API) and tracks its result.
 * Runs again when `key` changes (for example the month), and on `reload()`.
 *
 * Returns { status: "loading" | "ready" | "error", data, error, reload }.
 * On reload() (after a save), the old data stays on screen until the new data
 * arrives, so the page doesn't flash. When `key` changes, the old data is
 * dropped right away: showing October's numbers under "November" would be wrong.
 */
export function useLoad(load, key) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })
  const [version, setVersion] = useState(0)
  const lastKey = useRef(key)

  useEffect(() => {
    let cancelled = false
    const keyChanged = lastKey.current !== key
    lastKey.current = key
    if (keyChanged) setState({ status: 'loading', data: null, error: null })

    load().then(
      (data) => {
        if (!cancelled) setState({ status: 'ready', data, error: null })
      },
      (error) => {
        if (!cancelled) setState({ status: 'error', data: null, error })
      },
    )
    return () => {
      cancelled = true // ignore the answer if the page or month changed meanwhile
    }
    // `load` is left out on purpose: it's a new function on every render, and
    // only a new key or a reload() should fetch again.
  }, [key, version]) // eslint-disable-line react-hooks/exhaustive-deps

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  return { ...state, reload }
}
