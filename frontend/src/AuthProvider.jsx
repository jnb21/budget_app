import { useEffect, useMemo, useState } from 'react'
import * as api from './api.js'
import { AuthContext } from './authContext.js'

/**
 * Knows who is logged in, for every page.
 *
 * status: "checking" (asking the backend at startup) | "in" | "out"
 *       | "unreachable" (the backend didn't answer: we can't tell yet)
 *
 * Tests pass `initialUser` (a user, or null for "logged out") to skip the
 * startup check.
 */
export default function AuthProvider({ initialUser, children }) {
  const [state, setState] = useState(() =>
    initialUser === undefined
      ? { status: 'checking', user: null }
      : { status: initialUser ? 'in' : 'out', user: initialUser },
  )
  const [attempt, setAttempt] = useState(0)

  // At startup (and on "Try again"): ask the backend who we are.
  useEffect(() => {
    if (initialUser !== undefined && attempt === 0) return
    let cancelled = false
    api.getMe().then(
      (user) => { if (!cancelled) setState({ status: 'in', user }) },
      (error) => {
        if (!cancelled) setState({ status: error.status === 401 ? 'out' : 'unreachable', user: null })
      },
    )
    return () => { cancelled = true }
  }, [attempt]) // eslint-disable-line react-hooks/exhaustive-deps

  // Any API call answering 401 means the session is gone: show the login page.
  useEffect(() => {
    const onExpired = () => setState({ status: 'out', user: null })
    window.addEventListener(api.SESSION_EXPIRED, onExpired)
    return () => window.removeEventListener(api.SESSION_EXPIRED, onExpired)
  }, [])

  const value = useMemo(() => ({
    ...state,
    async logIn(email, password) {
      setState({ status: 'in', user: await api.logIn(email, password) })
    },
    async signUp(email, password) {
      setState({ status: 'in', user: await api.signUp(email, password) })
    },
    async logOut() {
      await api.logOut().catch(() => {}) // logged out locally even if the backend is down
      setState({ status: 'out', user: null })
    },
    /** After the account is deleted: forget the user without calling the backend. */
    forget() {
      setState({ status: 'out', user: null })
    },
    retry() {
      setState({ status: 'checking', user: null })
      setAttempt((a) => a + 1)
    },
  }), [state])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
