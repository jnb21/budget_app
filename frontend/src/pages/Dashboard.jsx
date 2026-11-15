import { Banknote, CircleAlert, DollarSign, PiggyBank, Plus } from 'lucide-react'
import { Link } from 'react-router'
import { getDashboard, getTransactions } from '../api.js'
import { categoryStyle, INCOME_CATEGORY } from '../categories.js'
import LoadState from '../components/LoadState.jsx'
import Money from '../components/Money.jsx'
import MonthPicker from '../components/MonthPicker.jsx'
import RingMeter from '../components/RingMeter.jsx'
import TransactionRow from '../components/TransactionRow.jsx'
import { formatMoneyShort, heroFigureClass } from '../money.js'
import { useMonth } from '../monthContext.js'
import { monthName } from '../months.js'
import { useLoad } from '../useLoad.js'

const RECENT_COUNT = 5
const INCOME_ICONS = [DollarSign, Banknote, PiggyBank]

export default function Dashboard() {
  const { month } = useMonth()
  const { status, data, error, reload } = useLoad(
    () => Promise.all([getDashboard(month), getTransactions(month)]).then(([dashboard, transactions]) => ({ dashboard, transactions })),
    month,
  )

  return (
    <main className="page">
      <header className="page-header">
        <div className="greeting">
          <span className="avatar" aria-hidden="true">
            DU
          </span>
          <div>
            <p className="greeting-hello">Hi there!</p>
            <h1 className="greeting-title">Monthly budget</h1>
          </div>
        </div>
        <MonthPicker />
      </header>

      {data ? <DashboardBody {...data} month={month} /> : <LoadState status={status} error={error} onRetry={reload} />}
    </main>
  )
}

function DashboardBody({ dashboard, transactions, month }) {
  const { budgeted_cents: budgeted, spent_cents: spent, categories } = dashboard
  const income = incomeSources(transactions)
  const recent = transactions.filter((t) => t.amount_cents < 0).slice(0, RECENT_COUNT)

  return (
    <>
      <section className="card hero" aria-labelledby="planned-heading">
        <div className="hero-text">
          <h2 id="planned-heading" className="eyebrow">
            <b>Planned</b> expenses
          </h2>
          <Money cents={budgeted} className={heroFigureClass(budgeted)} />
          <BudgetChip budgeted={budgeted} spent={spent} />
        </div>
        <RingMeter used={spent} limit={budgeted} label="spent" />
      </section>

      <section aria-labelledby="categories-heading">
        <h2 id="categories-heading" className="sr-only">
          Spending by category
        </h2>
        <ul className="carousel">
          <li>
            <Link to="/budgets" className="category-card category-card-add" aria-label="Set budgets">
              <Plus size={24} aria-hidden="true" />
            </Link>
          </li>
          {categories.map((line) => (
            <CategoryCard key={line.category_id ?? 'none'} line={line} />
          ))}
        </ul>
      </section>

      <section aria-labelledby="income-heading">
        <h2 id="income-heading" className="section-title">
          <b>My</b> income
        </h2>
        {income.length === 0 ? (
          <p className="empty">No income recorded in {monthName(month)} yet.</p>
        ) : (
          <ul className="income-grid">
            {income.map((source, i) => {
              const Icon = INCOME_ICONS[i % INCOME_ICONS.length]
              return (
                <li key={source.name} className="card income-card">
                  <span className="income-icon" aria-hidden="true">
                    <Icon size={20} strokeWidth={1.8} />
                  </span>
                  <span className="income-name">{source.name}</span>
                  <Money cents={source.cents} className="income-amount" />
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="recent-heading">
        <div className="section-header">
          <h2 id="recent-heading" className="section-title">
            <b>Spending</b> {monthName(month)}
          </h2>
          <Link to="/transactions" className="text-link">
            See all
          </Link>
        </div>
        {recent.length === 0 ? (
          <p className="empty">Nothing spent in {monthName(month)} yet.</p>
        ) : (
          <ul className="list">
            {recent.map((t) => (
              <TransactionRow key={t.id} transaction={t} showDate />
            ))}
          </ul>
        )}
      </section>
    </>
  )
}

/** "$1,180 left to spend", or "$32 over budget", or a link to set budgets. */
function BudgetChip({ budgeted, spent }) {
  if (budgeted === 0) {
    return (
      <Link to="/budgets" className="chip chip-outline">
        Set your first budget
      </Link>
    )
  }
  const left = budgeted - spent
  if (left < 0) {
    return (
      <span className="chip chip-critical">
        <CircleAlert size={14} aria-hidden="true" />
        {formatMoneyShort(-left)} over budget
      </span>
    )
  }
  return <span className="chip chip-outline">{formatMoneyShort(left)} left to spend</span>
}

/** A colored card per category: what was spent, and how much of its limit that is. */
function CategoryCard({ line }) {
  const { category_name: name, spent_cents: spent, limit_cents: limit, percent_used: percent, status } = line
  const { color, Icon } = categoryStyle(category(name))
  let note
  if (status === 'no_budget') note = 'No limit'
  else if (status === 'over') note = `Over by ${formatMoneyShort(spent - limit)}`
  else note = `${percent}% of ${formatMoneyShort(limit)}`

  return (
    <li className="category-card" style={{ '--cat': color }}>
      <span className="category-card-name">
        <Icon size={16} strokeWidth={2} aria-hidden="true" />
        {name}
      </span>
      <Money cents={spent} className="category-card-amount" />
      <span className={`category-card-note ${status}`}>
        {status === 'over' && <CircleAlert size={13} aria-hidden="true" />}
        {note}
      </span>
    </li>
  )
}

// The dashboard calls uncategorized spending "Uncategorized"; it has no style of its own.
const category = (name) => (name === 'Uncategorized' ? null : name)

/** Money received in the Income category, added up per description ("Salary": $5,600). */
function incomeSources(transactions) {
  const totals = new Map()
  for (const t of transactions) {
    if (t.amount_cents > 0 && t.category_name === INCOME_CATEGORY) {
      totals.set(t.description, (totals.get(t.description) ?? 0) + t.amount_cents)
    }
  }
  return [...totals].map(([name, cents]) => ({ name, cents })).sort((a, b) => b.cents - a.cents)
}
