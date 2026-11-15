import { X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'

/**
 * A panel that slides up from the bottom, over the page (a modal dialog).
 * Closes with Escape, the X button, or a click on the dimmed background.
 * Focus moves into it when it opens and back to where it was when it closes.
 */
export default function Sheet({ title, onClose, children }) {
  const titleId = useId()
  const panel = useRef(null)
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose // the Escape handler below always calls the latest onClose
  })

  useEffect(() => {
    const previous = document.activeElement
    const first = panel.current.querySelector('input, select, textarea, button:not(.sheet-close)')
    ;(first ?? panel.current).focus()

    function onKeyDown(event) {
      if (event.key === 'Escape') onCloseRef.current()
      if (event.key === 'Tab') keepFocusInside(event, panel.current)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      previous?.focus?.()
    }
  }, [])

  return (
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId} ref={panel} tabIndex={-1}>
        <div className="sheet-header">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="icon-button sheet-close" onClick={onClose} aria-label="Close">
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

/** Tab from the last control goes back to the first (and Shift+Tab the other way). */
function keepFocusInside(event, container) {
  const focusable = [...container.querySelectorAll('button, input, select, textarea, a[href]')].filter(
    (el) => !el.disabled,
  )
  if (focusable.length === 0) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
