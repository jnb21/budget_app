import { Check, Circle, Wallet, X } from 'lucide-react'
import { useId, useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router'
import { useAuth } from '../authContext.js'
import PasswordField from '../components/PasswordField.jsx'
import { brokenRules, PASSWORD_RULES } from '../passwordRules.js'

/** Log in (mode "login") or create an account (mode "signup"). */
export default function AuthPage({ mode }) {
  const auth = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const rulesId = useId()
  const matchId = useId()
  const signingUp = mode === 'signup'

  // Already logged in: go where the user was headed (or the dashboard).
  if (auth.status === 'in') return <Navigate to={location.state?.from ?? '/dashboard'} replace />

  const matches = confirm.length > 0 && confirm === password

  async function submit(event) {
    event.preventDefault()
    if (!email.trim() || !password) return setError('Enter your email and password.')
    if (signingUp) {
      const broken = brokenRules(password, email)
      if (broken.length > 0) return setError(`Your password needs: ${broken.map((r) => r.label.toLowerCase()).join(', ')}.`)
      if (!matches) return setError("The two passwords don't match.")
    }
    setBusy(true)
    setError(null)
    try {
      await (signingUp ? auth.signUp(email.trim(), password) : auth.logIn(email.trim(), password))
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="card auth-card">
        <div className="auth-brand">
          <span className="app-nav-logo" aria-hidden="true">
            <Wallet size={18} strokeWidth={2.2} />
          </span>
          <span>Budget</span>
        </div>
        <h1>{signingUp ? 'Create your account' : 'Welcome back'}</h1>
        <p className="auth-subtitle">
          {signingUp ? 'Track your spending and set a limit for each category.' : 'Log in to see your budget.'}
        </p>

        <form className="form" onSubmit={submit} noValidate aria-label={signingUp ? 'Sign up' : 'Log in'}>
          <label className="field">
            <span className="field-label">Email</span>
            <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>

          <PasswordField
            label="Password"
            value={password}
            onChange={setPassword}
            autoComplete={signingUp ? 'new-password' : 'current-password'}
            describedBy={signingUp ? rulesId : undefined}
          />

          {signingUp && (
            <>
              <ul id={rulesId} className="password-rules" aria-label="Password rules">
                {PASSWORD_RULES.map((rule) => {
                  const state = password === '' ? 'todo' : rule.passes(password, email) ? 'ok' : 'bad'
                  return (
                    <li key={rule.id} className={`rule rule-${state}`}>
                      {state === 'ok' && <Check size={14} aria-hidden="true" />}
                      {state === 'bad' && <X size={14} aria-hidden="true" />}
                      {state === 'todo' && <Circle size={10} aria-hidden="true" />}
                      <span>{rule.label}</span>
                      <span className="sr-only">{state === 'ok' ? ' (done)' : ' (not yet)'}</span>
                    </li>
                  )
                })}
              </ul>
              <p className="field-hint">Any characters work: letters in any language, spaces and symbols.</p>

              <PasswordField
                label="Confirm password"
                value={confirm}
                onChange={setConfirm}
                autoComplete="new-password"
                describedBy={matchId}
                invalid={confirm.length > 0 && !matches}
              />
              {confirm.length > 0 && (
                <p id={matchId} className={`rule ${matches ? 'rule-ok' : 'rule-bad'}`} aria-live="polite">
                  {matches ? <Check size={14} aria-hidden="true" /> : <X size={14} aria-hidden="true" />}
                  {matches ? 'Passwords match' : "Passwords don't match"}
                </p>
              )}
            </>
          )}

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="button button-primary auth-submit" disabled={busy}>
            {signingUp ? 'Create account' : 'Log in'}
          </button>
        </form>

        <p className="auth-switch">
          {signingUp ? (
            <>Already have an account? <Link to="/login">Log in</Link></>
          ) : (
            <>New here? <Link to="/signup">Create an account</Link></>
          )}
        </p>
      </div>
    </main>
  )
}
