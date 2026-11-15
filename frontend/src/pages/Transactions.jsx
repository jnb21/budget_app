import { Plus, TrendingDown, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { getCategories, getDashboard, getTransactions } from '../api.js'
import LoadState from '../components/LoadState.jsx'
import Money from '../components/Money.jsx'
import MonthPicker from '../components/MonthPicker.jsx'
import Sheet from '../components/Sheet.jsx'
import SpendingBar from '../components/SpendingBar.jsx'
import TransactionForm from '../components/TransactionForm.jsx'
import TransactionRow from '../components/TransactionRow.jsx'
import { heroFigureClass } from '../money.js'
import { useMonth } from '../monthContext.js'
import { currentMonth, defaultDayFor, formatDay, monthName, shiftMonth, shortMonthName } from '../months.js'
import { spentThrough } from '../spending.js'
import { useLoad } from '../useLoad.js'

export default function Transactions() {
  const { month } = useMonth()
  const previous = shiftMonth(month, -1)
  const { status, data, error, reload } = useLoad(
    () =>
      Promise.all([getDashboard(month), getTransactions(month), getTransactions(previous), getCategories()]).then(
        // `today` is read here, once per load, not on every render
        ([dashboard, transactions, previousTransactions, categories]) => ({ dashboard, transactions, previousTransactions, categories, today: new Date() }),
      ),
    month,
  )
  // null = closed, "new" = adding, a transaction = editing it
  const [editing, setEditing] = useState(null)

  function saved() {
    setEditing(null)
    reload()
  }

  return (
    <main className="page">
      <header className="page-header">
        <h1 className="page-title">Transactions</h1>
        <MonthPicker />
      </header>

      {data ? <TransactionsBody {...data} month={month} onSelect={setEditing} onAdd={() => setEditing('new')} /> : <LoadState status={status} error={error} onRetry={reload} />}

      {editing && data && (
        <Sheet title={editing === 'new' ? 'New transaction' : 'Edit transaction'} onClose={() => setEditing(null)}>
          <TransactionForm
            transaction={editing === 'new' ? null : editing}
            categories={data.categories}
            defaultDate={defaultDayFor(month)}
            onSaved={saved}
          />
        </Sheet>
      )}
    </main>
  )
}

function TransactionsBody({ dashboard, transactions, previousTransactions, today, month, onSelect, onAdd }) {
  const days = groupByDay(transactions)

  // Phones: one column. Desktop: the list on the left, the summary in a sticky column on the right.
  return (
    <div className="split-layout">
      <div className="split-side">
        <section className="card balance" aria-labelledby="net-heading">
          <div className="balance-header">
            <h2 id="net-heading" className="eyebrow">
              Net for {monthName(month)}
            </h2>
            <button type="button" className="icon-button icon-button-accent" onClick={onAdd} aria-label="New transaction" title="New transaction">
              <Plus size={20} aria-hidden="true" />
            </button>
          </div>
          <Money cents={dashboard.net_cents} className={heroFigureClass(dashboard.net_cents)} />
          <SpendingChange month={month} transactions={transactions} previousTransactions={previousTransactions} today={today} />
          <dl className="balance-split">
            <div>
              <dt>Money in</dt>
              <dd>
                <Money cents={dashboard.income_cents} plus className="received" />
              </dd>
            </div>
            <div>
              <dt>Money out</dt>
              <dd>
                <Money cents={dashboard.spent_cents} />
              </dd>
            </div>
          </dl>
        </section>

        <section className="card" aria-labelledby="split-heading">
          <div className="section-header">
            <h2 id="split-heading" className="section-title">
              <b>Spending</b> {monthName(month)}
            </h2>
            <Money cents={dashboard.spent_cents} className="section-amount" />
          </div>
          {dashboard.spent_cents > 0 ? <SpendingBar lines={dashboard.categories} /> : <p className="empty">Nothing spent yet.</p>}
        </section>
      </div>

      <div className="split-main">
        {days.length === 0 ? (
          <div className="card empty-card">
            <p>No transactions in {monthName(month)} yet.</p>
            <button type="button" className="button button-primary" onClick={onAdd}>
              Add a transaction
            </button>
          </div>
        ) : (
          days.map(([day, items]) => (
            <section key={day} aria-label={formatDay(day)}>
              <h2 className="day-heading">{formatDay(day)}</h2>
              <ul className="list">
                {items.map((t) => (
                  <TransactionRow key={t.id} transaction={t} onSelect={onSelect} />
                ))}
              </ul>
            </section>
          ))
        )}
      </div>
    </div>
  )
}

/**
 * "↘ 8% less spent than Oct" (green) or "↗ 12% more spent than Oct" (amber).
 * In the current month, it compares the same days: Nov 1–15 against Oct 1–15,
 * because half a month always looks cheaper than a whole one.
 */
function SpendingChange({ month, transactions, previousTransactions, today }) {
  const previous = shiftMonth(month, -1)
  const ongoing = month === currentMonth(today)
  const lastDay = ongoing ? today.getDate() : 31
  const spent = spentThrough(transactions, lastDay)
  const before = spentThrough(previousTransactions, lastDay)
  if (before === 0 || spent === 0) return null

  const than = ongoing ? `${shortMonthName(previous)} 1–${lastDay}` : monthName(previous)
  const change = Math.round(((spent - before) / before) * 100)
  if (change === 0) return <span className="chip chip-muted">Same spending as {than}</span>
  const less = change < 0
  const Icon = less ? TrendingDown : TrendingUp
  return (
    <span className={`chip ${less ? 'chip-good' : 'chip-warning'}`}>
      <Icon size={14} aria-hidden="true" />
      {Math.abs(change)}% {less ? 'less' : 'more'} spent than {than}
    </span>
  )
}

/** Newest day first (the API already sorts newest first): [["2026-11-14", [...]], ...] */
function groupByDay(transactions) {
  const days = new Map()
  for (const t of transactions) {
    if (!days.has(t.posted_date)) days.set(t.posted_date, [])
    days.get(t.posted_date).push(t)
  }
  return [...days]
}
