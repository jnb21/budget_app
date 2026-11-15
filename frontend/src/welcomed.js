// Remembers (in this browser) that the welcome screen was seen, so "/" goes
// straight to the dashboard next time. localStorage can throw (private mode,
// storage disabled): then the welcome screen simply shows again.

const KEY = 'budget-app.welcomed'

export function hasBeenWelcomed() {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

export function markWelcomed() {
  try {
    localStorage.setItem(KEY, '1')
  } catch {
    // nothing to do: see above
  }
}
