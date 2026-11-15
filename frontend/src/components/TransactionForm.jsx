import { useState } from 'react'
import { createTransaction, deleteTransaction, updateTransaction } from '../api.js'
import { INCOME_CATEGORY } from '../categories.js'
import { centsToInput, parseAmount } from '../money.js'

/**
 * Add a transaction, or edit/delete one (when `transaction` is given).
 * `categories` come from GET /api/categories. Calls onSaved() after any change.
 */
export default function TransactionForm({ transaction, categories, defaultDate, onSaved }) {
  const editing = Boolean(transaction)
  const incomeCategory = categories.find((c) => c.name === INCOME_CATEGORY)
  const [kind, setKind] = useState(transaction && transaction.amount_cents > 0 ? 'income' : 'expense')
  const [amount, setAmount] = useState(transaction ? centsToInput(Math.abs(transaction.amount_cents)) : '')
  const [description, setDescription] = useState(transaction?.description ?? '')
  const [categoryId, setCategoryId] = useState(transaction?.category_id ? String(transaction.category_id) : '')
  const [date, setDate] = useState(transaction?.posted_date ?? defaultDate)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  function chooseKind(next) {
    setKind(next)
    // Money in is almost always Income: pick it unless a category is already chosen.
    if (next === 'income' && categoryId === '' && incomeCategory) setCategoryId(String(incomeCategory.id))
    if (next === 'expense' && incomeCategory && categoryId === String(incomeCategory.id)) setCategoryId('')
  }

  async function submit(event) {
    event.preventDefault()
    const cents = parseAmount(amount)
    if (cents === null) return setError('Enter an amount, like 12.50.')
    if (cents === 0) return setError("The amount can't be zero.")
    if (!description.trim()) return setError('Add a description.')
    if (!date) return setError('Pick a date.')

    const draft = {
      posted_date: date,
      amount_cents: kind === 'expense' ? -cents : cents,
      description: description.trim(),
      category_id: categoryId === '' ? null : Number(categoryId),
    }
    await run(() => (editing ? updateTransaction(transaction.id, draft) : createTransaction(draft)))
  }

  async function remove() {
    if (!confirmingDelete) return setConfirmingDelete(true)
    await run(() => deleteTransaction(transaction.id))
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
      <div className="segmented" role="radiogroup" aria-label="Type">
        {['expense', 'income'].map((option) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={kind === option}
            className={kind === option ? 'active' : ''}
            onClick={() => chooseKind(option)}
          >
            {option === 'expense' ? 'Expense' : 'Income'}
          </button>
        ))}
      </div>

      <label className="field">
        <span className="field-label">Amount</span>
        <span className="amount-input">
          <span aria-hidden="true">$</span>
          <input inputMode="decimal" autoComplete="off" placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </span>
      </label>

      <label className="field">
        <span className="field-label">Description</span>
        <input maxLength={200} placeholder={kind === 'expense' ? 'Groceries at Metro' : 'Salary'} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>

      <div className="field-row">
        <label className="field">
          <span className="field-label">Category</span>
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">Uncategorized</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Date</span>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="form-actions">
        {editing && (
          <button type="button" className={`button ${confirmingDelete ? 'button-danger' : ''}`} onClick={remove} disabled={busy}>
            {confirmingDelete ? 'Tap again to delete' : 'Delete'}
          </button>
        )}
        <button type="submit" className="button button-primary" disabled={busy}>
          {editing ? 'Save changes' : 'Add transaction'}
        </button>
      </div>
    </form>
  )
}
