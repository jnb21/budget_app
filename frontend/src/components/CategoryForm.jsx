import { useState } from 'react'
import { createCategory } from '../api.js'

/** Create a category of your own (the backend answers 409 if the name exists). */
export default function CategoryForm({ onSaved }) {
  const [name, setName] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    if (!name.trim()) return setError('Give the category a name.')
    setBusy(true)
    setError(null)
    try {
      await createCategory(name.trim())
      onSaved()
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <label className="field">
        <span className="field-label">Name</span>
        <input maxLength={50} placeholder="Pets" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button type="submit" className="button button-primary" disabled={busy}>
          Create category
        </button>
      </div>
    </form>
  )
}
