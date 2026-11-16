import { Eye, EyeOff } from 'lucide-react'
import { useId, useState } from 'react'

/**
 * A password input with a show/hide button. The button sits outside the
 * <label> (linked by htmlFor/id instead), so the field's name stays just
 * "Password" for screen readers. `describedBy` links hints or the rule list.
 */
export default function PasswordField({ label, value, onChange, autoComplete, describedBy, invalid }) {
  const [visible, setVisible] = useState(false)
  const id = useId()
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>{label}</label>
      <span className="password-input">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          maxLength={128}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
        />
        <button
          type="button"
          className="icon-button password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
        >
          {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </span>
    </div>
  )
}
