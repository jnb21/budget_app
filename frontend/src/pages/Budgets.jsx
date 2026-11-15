import { CircleAlert, Plus } from 'lucide-react'
import { useState } from 'react'
import { getBudgets, getCategories, getDashboard } from '../api.js'
import { INCOME_CATEGORY } from '../categories.js'
import BudgetForm from '../components/BudgetForm.jsx'
import CategoryForm from '../components/CategoryForm.jsx'
import CategoryIcon from '../components/CategoryIcon.jsx'
import LoadState from '../components/LoadState.jsx'
import Money from '../components/Money.jsx'
import MonthPicker from '../components/MonthPicker.jsx'
import Sheet from '../components/Sheet.jsx'
import { formatMoney, formatMoneyShort, heroFigureClass } from '../money.js'
import { useMonth } from '../monthContext.js'
import { monthName } from '../months.js'
import { useLoad } from '../useLoad.js'

const NEAR_LIMIT_PERCENT = 80 // same threshold as the backend's dashboard

export default function Budgets() {
  const { month } = useMonth()
  const { status, data, error, reload } = useLoad(
    () =>
      Promise.all([getCategories(), getBudgets(month), getDashboard(month)]).then(([categories, budgets, dashboard]) =>
        buildRows(categories, budgets, dashboard),
      ),
    month,
  )
  // null = closed, "category" = new category, a row = editing that row's limit
  const [open, setOpen] = useState(null)

  function saved() {
    setOpen(null)
    reload()
  }

  return (
    <main className="page">
      <header className="page-header">
        <h1 className="page-title">Budgets</h1>
        <MonthPicker />
      </header>

      {data ? <BudgetsBody {...data} month={month} onEdit={setOpen} onNewCategory={() => setOpen('category')} /> : <LoadState status={status} error={error} onRetry={reload} />}

      {open === 'category' && (
        <Sheet title="New category" onClose={() => setOpen(null)}>
          <CategoryForm onSaved={saved} />
        </Sheet>
      )}
      {open && open !== 'category' && (
        <Sheet title={`${open.category.name} limit for ${monthName(month)}`} onClose={() => setOpen(null)}>
          <BudgetForm category={open.category} budget={open.budget} month={month} spentCents={open.spent} onSaved={saved} />
        </Sheet>
      )}
    </main>
  )
}

function BudgetsBody({ budgeted, unbudgeted, totalLimit, totalSpentBudgeted, month, onEdit, onNewCategory }) {
  return (
    <>
      <section className="card hero-compact" aria-labelledby="planned-total">
        <h2 id="planned-total" className="eyebrow">
          <b>Planned</b> for {monthName(month)}
        </h2>
        <Money cents={totalLimit} className={heroFigureClass(totalLimit)} />
        <p className="muted">
          {budgeted.length === 0
            ? 'No limits yet. Pick a category below to set one.'
            : `${formatMoney(totalSpentBudgeted)} spent across ${budgeted.length} ${budgeted.length === 1 ? 'category' : 'categories'} with a limit`}
        </p>
      </section>

      {budgeted.length > 0 && (
        <section aria-labelledby="with-limit">
          <h2 id="with-limit" className="section-title">
            <b>With</b> a limit
          </h2>
          <ul className="list">
            {budgeted.map((row) => (
              <BudgetRow key={row.category.id} row={row} onEdit={onEdit} />
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="without-limit">
        <h2 id="without-limit" className="section-title">
          <b>No</b> limit yet
        </h2>
        <ul className="list">
          {unbudgeted.map((row) => (
            <BudgetRow key={row.category.id} row={row} onEdit={onEdit} />
          ))}
        </ul>
        <button type="button" className="button button-ghost add-category" onClick={onNewCategory}>
          <Plus size={18} aria-hidden="true" /> New category
        </button>
      </section>
    </>
  )
}

/** A category with its limit: name, a meter bar, and "$412 of $550". The whole row opens the limit editor. */
function BudgetRow({ row, onEdit }) {
  const { category, budget, spent } = row
  const percent = budget ? Math.floor((spent * 100) / budget.limit_cents) : null
  const state = !budget ? 'none' : spent > budget.limit_cents ? 'over' : percent >= NEAR_LIMIT_PERCENT ? 'near' : 'ok'

  return (
    <li className="row">
      <button type="button" className="row-inner budget-row" onClick={() => onEdit(row)} aria-label={`${category.name}: ${describe(row, percent)}. Edit limit`}>
        <CategoryIcon name={category.name} />
        <span className="row-text">
          <span className="row-title">{category.name}</span>
          {budget ? (
            <span className={`meter meter-${state}`} aria-hidden="true">
              <span style={{ width: `${Math.min(percent, 100)}%` }} />
            </span>
          ) : (
            <span className="row-subtitle">{spent > 0 ? `${formatMoney(spent)} spent` : 'Nothing spent'}</span>
          )}
        </span>
        <span className="budget-figure" aria-hidden="true">
          {budget ? (
            <>
              <span className={`budget-spent ${state}`}>
                {state === 'over' && <CircleAlert size={13} />}
                {formatMoneyShort(spent)}
              </span>
              <span className="budget-limit">of {formatMoneyShort(budget.limit_cents)}</span>
            </>
          ) : (
            <span className="set-limit">Set limit</span>
          )}
        </span>
      </button>
    </li>
  )
}

function describe({ budget, spent }, percent) {
  if (!budget) return `no limit, ${formatMoney(spent)} spent`
  const over = spent > budget.limit_cents ? `, over by ${formatMoney(spent - budget.limit_cents)}` : ''
  return `${formatMoney(spent)} of ${formatMoney(budget.limit_cents)} spent, ${percent}%${over}`
}

/** One row per spending category (Income isn't spending), split into "has a limit" and "doesn't". */
function buildRows(categories, budgets, dashboard) {
  const budgetByCategory = new Map(budgets.map((b) => [b.category_id, b]))
  const spentByCategory = new Map(dashboard.categories.map((line) => [line.category_id, line.spent_cents]))
  const rows = categories
    .filter((c) => c.name !== INCOME_CATEGORY)
    .map((category) => ({
      category,
      budget: budgetByCategory.get(category.id) ?? null,
      spent: spentByCategory.get(category.id) ?? 0,
    }))
  const budgeted = rows.filter((r) => r.budget).sort((a, b) => b.budget.limit_cents - a.budget.limit_cents)
  const unbudgeted = rows.filter((r) => !r.budget).sort((a, b) => b.spent - a.spent || a.category.name.localeCompare(b.category.name))
  return {
    budgeted,
    unbudgeted,
    totalLimit: budgeted.reduce((sum, r) => sum + r.budget.limit_cents, 0),
    totalSpentBudgeted: budgeted.reduce((sum, r) => sum + r.spent, 0),
  }
}
