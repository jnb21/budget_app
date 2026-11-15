import { categoryStyle, NEUTRAL_COLOR } from '../categories.js'
import { formatMoney } from '../money.js'

const MAX_PARTS = 5 // past this, the smallest categories fold into "Other"

/**
 * One month's spending split by category: a thin bar (each part as wide as its
 * share) and a legend under it with each part's name and amount, in bar order.
 * `lines` are the dashboard's categories: [{ category_name, spent_cents }].
 */
export default function SpendingBar({ lines }) {
  const parts = foldParts(lines.filter((line) => line.spent_cents > 0))
  const total = parts.reduce((sum, part) => sum + part.cents, 0)
  if (total === 0) return null

  const describe = (part) => `${part.name} ${formatMoney(part.cents)} (${Math.round((part.cents / total) * 100)}%)`

  return (
    <div className="spending-bar">
      <div className="spending-bar-track" role="img" aria-label={`Spending by category: ${parts.map(describe).join(', ')}`}>
        {parts.map((part) => (
          <span
            key={part.name}
            className="spending-bar-part"
            style={{ flexGrow: part.cents, background: part.color }}
            title={describe(part)}
          />
        ))}
      </div>
      <ul className="legend">
        {parts.map((part) => (
          <li key={part.name}>
            <span className="swatch" style={{ background: part.color }} aria-hidden="true" />
            {part.name} <span className="legend-amount">{formatMoney(part.cents)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Largest first; everything past MAX_PARTS - 1 becomes one gray "Other" part. */
function foldParts(lines) {
  const sorted = [...lines].sort((a, b) => b.spent_cents - a.spent_cents)
  const parts = sorted.map((line) => ({
    name: line.category_name,
    cents: line.spent_cents,
    color: categoryStyle(line.category_name).color,
  }))
  if (parts.length <= MAX_PARTS) return parts
  const kept = parts.slice(0, MAX_PARTS - 1)
  const rest = parts.slice(MAX_PARTS - 1).reduce((sum, part) => sum + part.cents, 0)
  return [...kept, { name: 'Other', cents: rest, color: NEUTRAL_COLOR }]
}
