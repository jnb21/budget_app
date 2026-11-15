import { formatShortDay } from '../months.js'
import CategoryIcon from './CategoryIcon.jsx'
import Money from './Money.jsx'

/**
 * One transaction: icon, description, category (and date), amount.
 * Money received shows as "+$25.00" in green; money spent as "$54.99".
 * With `onSelect`, the whole row is a button that opens it for editing.
 */
export default function TransactionRow({ transaction, showDate = false, onSelect }) {
  const { description, category_name, posted_date, amount_cents } = transaction
  const details = [category_name ?? 'Uncategorized', showDate && formatShortDay(posted_date)].filter(Boolean).join(' • ')
  const content = (
    <>
      <CategoryIcon name={category_name} />
      <span className="row-text">
        <span className="row-title">{description}</span>
        <span className="row-subtitle">{details}</span>
      </span>
      <Money cents={amount_cents > 0 ? amount_cents : -amount_cents} plus={amount_cents > 0} className={amount_cents > 0 ? 'row-amount received' : 'row-amount'} />
    </>
  )
  return (
    <li className="row">
      {onSelect ? (
        <button type="button" className="row-inner" onClick={() => onSelect(transaction)}>
          {content}
        </button>
      ) : (
        <div className="row-inner">{content}</div>
      )}
    </li>
  )
}
