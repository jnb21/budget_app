import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useMonth } from '../monthContext.js'
import { monthLabel, shiftMonth, shortMonthName } from '../months.js'

/** "‹ Nov 2026 ›": changes the month for every page. */
export default function MonthPicker() {
  const { month, setMonth } = useMonth()
  return (
    <div className="month-picker" role="group" aria-label="Month">
      <button type="button" className="icon-button" onClick={() => setMonth(shiftMonth(month, -1))} aria-label="Previous month">
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
      <span className="month-picker-label" aria-live="polite">
        <span className="dot" aria-hidden="true" />
        <span aria-hidden="true">{shortMonthName(month)} {month.slice(0, 4)}</span>
        <span className="sr-only">{monthLabel(month)}</span>
      </span>
      <button type="button" className="icon-button" onClick={() => setMonth(shiftMonth(month, 1))} aria-label="Next month">
        <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>
  )
}
