import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router'
import { useAuth } from './authContext.js'
import AppNav from './components/AppNav.jsx'
import Account from './pages/Account.jsx'
import AuthPage from './pages/AuthPage.jsx'
import Budgets from './pages/Budgets.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Status from './pages/Status.jsx'
import Transactions from './pages/Transactions.jsx'
import Welcome from './pages/Welcome.jsx'
import { hasBeenWelcomed } from './welcomed.js'
import './App.css'

/** Page URLs. The router itself (BrowserRouter) is in main.jsx, so tests can use a MemoryRouter. */
export default function App() {
  return (
    <Routes>
      <Route index element={<Navigate to={hasBeenWelcomed() ? '/dashboard' : '/welcome'} replace />} />
      <Route path="welcome" element={<Welcome />} />
      <Route path="login" element={<AuthPage mode="login" />} />
      <Route path="signup" element={<AuthPage mode="signup" />} />
      <Route element={<Shell />}>
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="budgets" element={<Budgets />} />
        <Route path="account" element={<Account />} />
      </Route>
      <Route path="status" element={<Status />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

/**
 * Every page that shows your data: only when logged in (else the login page,
 * which comes back here afterwards). Then the nav (bottom pill on phones,
 * sidebar on desktop), then the page.
 */
function Shell() {
  const auth = useAuth()
  const location = useLocation()

  if (auth.status === 'checking') {
    return (
      <div className="load-state" role="status">
        <span className="spinner" aria-hidden="true" />
        Loading…
      </div>
    )
  }
  if (auth.status === 'unreachable') {
    return (
      <main className="auth-page">
        <div className="card load-state load-error" role="alert">
          <p>Can't reach the server. Is the backend running?</p>
          <button type="button" className="button button-primary" onClick={auth.retry}>Try again</button>
        </div>
      </main>
    )
  }
  if (auth.status === 'out') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return (
    <div className="shell">
      <AppNav />
      <Outlet />
    </div>
  )
}
