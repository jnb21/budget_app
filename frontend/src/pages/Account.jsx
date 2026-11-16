import { Download, LogOut, Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { deleteCategory, deleteMyAccount, exportMyData, getCategories, renameCategory } from '../api.js'
import { initials, useAuth } from '../authContext.js'
import CategoryIcon from '../components/CategoryIcon.jsx'
import LoadState from '../components/LoadState.jsx'
import Sheet from '../components/Sheet.jsx'
import { useLoad } from '../useLoad.js'

/** Your account: who you are, your own categories, your data, log out, delete. */
export default function Account() {
  const auth = useAuth()
  const categories = useLoad(getCategories, 'categories')
  const [open, setOpen] = useState(null) // { kind: "rename" | "remove" | "delete-account", category? }
  const own = (categories.data ?? []).filter((c) => !c.is_default)

  function done() {
    setOpen(null)
    categories.reload()
  }

  return (
    <main className="page account-page">
      <header className="page-header">
        <h1>Account</h1>
      </header>

      <section className="card account-who">
        <span className="avatar" aria-hidden="true">{initials(auth.user.email)}</span>
        <div>
          <p className="account-email">{auth.user.email}</p>
          <p className="muted">Logged in</p>
        </div>
        <button type="button" className="button" onClick={auth.logOut}>
          <LogOut size={16} aria-hidden="true" /> Log out
        </button>
      </section>

      <h2 className="section-title"><b>My</b> categories</h2>
      {categories.status !== 'ready' ? (
        <LoadState status={categories.status} error={categories.error} onRetry={categories.reload} />
      ) : own.length === 0 ? (
        <p className="card muted account-empty">You haven't created any categories. You can add one from the Budgets page.</p>
      ) : (
        <ul className="card account-categories">
          {own.map((c) => (
            <li key={c.id}>
              <CategoryIcon name={c.name} size={36} />
              <span className="account-category-name">{c.name}</span>
              <button type="button" className="icon-button" aria-label={`Rename ${c.name}`}
                      onClick={() => setOpen({ kind: 'rename', category: c })}>
                <Pencil size={16} aria-hidden="true" />
              </button>
              <button type="button" className="icon-button" aria-label={`Delete ${c.name}`}
                      onClick={() => setOpen({ kind: 'remove', category: c })}>
                <Trash2 size={16} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <h2 className="section-title"><b>My</b> data</h2>
      <section className="card account-actions">
        <div>
          <p className="account-action-title">Download my data</p>
          <p className="muted">Everything stored about you, as a JSON file.</p>
        </div>
        <DownloadButton />
      </section>
      <section className="card account-actions account-danger">
        <div>
          <p className="account-action-title">Delete my account</p>
          <p className="muted">Removes your account and all your transactions, budgets and categories. This can't be undone.</p>
        </div>
        <button type="button" className="button button-danger" onClick={() => setOpen({ kind: 'delete-account' })}>
          Delete account
        </button>
      </section>

      {open?.kind === 'rename' && (
        <Sheet title={`Rename ${open.category.name}`} onClose={() => setOpen(null)}>
          <RenameForm category={open.category} onSaved={done} />
        </Sheet>
      )}
      {open?.kind === 'remove' && (
        <Sheet title={`Delete ${open.category.name}?`} onClose={() => setOpen(null)}>
          <RemoveCategory category={open.category} onDone={done} onCancel={() => setOpen(null)} />
        </Sheet>
      )}
      {open?.kind === 'delete-account' && (
        <Sheet title="Delete your account?" onClose={() => setOpen(null)}>
          <DeleteAccountForm onDeleted={auth.forget} />
        </Sheet>
      )}
    </main>
  )
}

function DownloadButton() {
  const [error, setError] = useState(null)

  async function download() {
    try {
      const data = await exportMyData()
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a')
      link.href = url
      link.download = 'budget-app-my-data.json'
      link.click()
      URL.revokeObjectURL(url)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="account-action-button">
      <button type="button" className="button" onClick={download}>
        <Download size={16} aria-hidden="true" /> Download
      </button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  )
}

function RenameForm({ category, onSaved }) {
  const [name, setName] = useState(category.name)
  const [error, setError] = useState(null)

  async function submit(event) {
    event.preventDefault()
    if (!name.trim()) return setError('Give the category a name.')
    try {
      await renameCategory(category.id, name.trim())
      onSaved()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate>
      <label className="field">
        <span className="field-label">Name</span>
        <input maxLength={50} value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="submit" className="button button-primary">Save</button>
      </div>
    </form>
  )
}

function RemoveCategory({ category, onDone, onCancel }) {
  const [error, setError] = useState(null)

  async function remove() {
    try {
      await deleteCategory(category.id)
      onDone()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="form">
      <p>Its transactions will become <b>Uncategorized</b>, and its budgets will be removed.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="button" className="button" onClick={onCancel}>Cancel</button>
        <button type="button" className="button button-danger" onClick={remove}>Delete category</button>
      </div>
    </div>
  )
}

function DeleteAccountForm({ onDeleted }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    if (!password) return setError('Enter your password to confirm.')
    setBusy(true)
    try {
      await deleteMyAccount(password)
      onDeleted()
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <form className="form" onSubmit={submit} noValidate aria-label="Delete account">
      <p>All your transactions, budgets and categories will be deleted. This can't be undone.</p>
      <label className="field">
        <span className="field-label">Password</span>
        <input type="password" autoComplete="current-password" value={password}
               onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="submit" className="button button-danger" disabled={busy}>Delete my account</button>
      </div>
    </form>
  )
}
