/**
 * How much of a limit is used, as a ring: one value against one limit (a meter).
 * The fill carries the state: violet under 80%, amber from 80%, red past 100%.
 * The track is a light step of the same color, so the state reads around the whole ring.
 * The percent is rounded down, like the backend's percent_used.
 */
export default function RingMeter({ used, limit, label, size = 116, stroke = 14 }) {
  const ratio = limit > 0 ? used / limit : 0
  const percent = Math.floor(ratio * 100)
  const state = limit <= 0 ? 'empty' : ratio > 1 ? 'over' : percent >= 80 ? 'near' : 'ok'
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const filled = Math.min(ratio, 1) * circumference

  return (
    <figure className={`ring ring-${state}`} style={{ '--ring-size': `${size}px` }} role="img" aria-label={limit > 0 ? `${percent}% of the budget ${label}` : 'No budget set'}>
      <svg viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle className="ring-track" cx={size / 2} cy={size / 2} r={radius} strokeWidth={stroke} fill="none" />
        {filled > 0 && (
          <circle
            className="ring-fill"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={stroke}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference}`}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        )}
      </svg>
      <figcaption aria-hidden="true">
        <strong>{limit > 0 ? `${percent}%` : '—'}</strong>
        <span>{limit > 0 ? label : 'no budget'}</span>
      </figcaption>
    </figure>
  )
}
