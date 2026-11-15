import { Navigate, Outlet, Route, Routes } from 'react-router'
import AppNav from './components/AppNav.jsx'
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
      <Route element={<Shell />}>
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="budgets" element={<Budgets />} />
        <Route path="status" element={<Status />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

/** Every page but the welcome screen: the nav (bottom pill on phones, sidebar on desktop), then the page. */
function Shell() {
  return (
    <div className="shell">
      <AppNav />
      <Outlet />
    </div>
  )
}
