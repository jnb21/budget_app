import { ArrowLeftRight, ChartPie, Wallet } from 'lucide-react'
import { NavLink } from 'react-router'

const LINKS = [
  { to: '/dashboard', label: 'Dashboard', Icon: ChartPie },
  { to: '/transactions', label: 'Transactions', Icon: ArrowLeftRight },
  { to: '/budgets', label: 'Budgets', Icon: Wallet },
]

/** The floating pill at the bottom of the screen. The current page's icon sits in a violet circle. */
export default function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Main">
      {LINKS.map(({ to, label, Icon }) => (
        <NavLink key={to} to={to} className="bottom-nav-link" aria-label={label} title={label}>
          <Icon size={22} strokeWidth={1.8} aria-hidden="true" />
        </NavLink>
      ))}
    </nav>
  )
}
