import { useState } from 'react'
import { deleteBudget, setBudget } from '../api.js'
import { centsToInput, formatMoney, parseAmount } from '../money.js'
import { monthName } from '../months.js'

/**
 * Set (or change, or remove) one category's limit for one month.
 * `budget` is the existing budget or null; `spentCents` is shown for context.
 */
export default function BudgetForm({ category, budget, month, spentCents, onSaved }) {
  const [amount, setAmount] = useState(budget ? centsToInput(budget.limit_cents) : '')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    const cents = parseAmount(amount)
    if (cents === null || cents === 0) return setError('Enter a limit, like 150.')
    await run(() => setBudget(category.id, month, cents))
  }

  async function run(action) {
    setBusy(true)
    setError(null)
    try {
      await action()
      onSaved()
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <p className="form-hint">
        Spent on {category.name.toLowerCase()} in {monthName(month)} so far: <strong>{formatMoney(spentCents)}</strong>
      </p>
      <label className="field">
        <span className="field-label">Monthly limit</span>
        <span className="amount-input">
          <span aria-hidden="true">$</span>
          <input inputMode="decimal" autoComplete="off" placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </span>
      </label>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="form-actions">
        {budget && (
          <button type="button" className="button" onClick={() => run(() => deleteBudget(budget.id))} disabled={busy}>
            Remove limit
          </button>
        )}
        <button type="submit" className="button button-primary" disabled={busy}>
          {budget ? 'Save limit' : 'Set limit'}
        </button>
      </div>
    </form>
  )
}
