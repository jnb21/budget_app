import { Activity, ArrowLeftRight, ChartPie, LogOut, UserRound, Wallet } from 'lucide-react'
import { NavLink } from 'react-router'
import { initials, useAuth } from '../authContext.js'

const LINKS = [
  { to: '/dashboard', label: 'Dashboard', Icon: ChartPie },
  { to: '/transactions', label: 'Transactions', Icon: ArrowLeftRight },
  { to: '/budgets', label: 'Budgets', Icon: Wallet },
  { to: '/account', label: 'Account', Icon: UserRound },
]

/**
 * The main navigation, one component for both layouts (App.css decides):
 * - phone: a floating pill at the bottom, icons only (labels are for screen readers)
 * - desktop: a sidebar on the left with the app name, labels, and the user at the bottom
 *   (from 960px an icon rail, from 1200px with labels)
 */
export default function AppNav() {
  const auth = useAuth()
  return (
    <nav className="app-nav" aria-label="Main">
      <div className="app-nav-brand desktop-only">
        <span className="app-nav-logo" aria-hidden="true">
          <Wallet size={18} strokeWidth={2.2} />
        </span>
        <span className="app-nav-brand-name">Budget</span>
      </div>

      <div className="app-nav-links">
        {LINKS.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} className="app-nav-link" title={label}>
            <Icon size={22} strokeWidth={1.8} aria-hidden="true" />
            <span className="app-nav-label">{label}</span>
          </NavLink>
        ))}
      </div>

      <div className="app-nav-footer desktop-only">
        <NavLink to="/status" className="app-nav-status" title="Backend status">
          <Activity size={16} aria-hidden="true" />
          <span className="app-nav-label">Backend status</span>
        </NavLink>
        <div className="app-nav-user">
          <span className="avatar avatar-small" aria-hidden="true">
            {initials(auth.user.email)}
          </span>
          <span className="app-nav-user-text">
            <span className="app-nav-user-name">{auth.user.email}</span>
          </span>
          <button type="button" className="icon-button app-nav-logout" onClick={auth.logOut}
                  aria-label="Log out" title="Log out">
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </nav>
  )
}
