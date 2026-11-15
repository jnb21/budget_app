import { splitCents } from '../money.js'

/**
 * An amount with small cents, like "$1,475.00" where ".00" is smaller.
 * `plus` puts a "+" on positive amounts (money received).
 * Screen readers still read it as one amount: it's plain inline text.
 */
export default function Money({ cents, plus = false, className = '' }) {
  const { negative, dollars, cents: rest } = splitCents(cents)
  const sign = negative ? '−' : plus && cents > 0 ? '+' : ''
  return (
    <span className={`money ${className}`}>
      {sign}${dollars}
      <span className="money-cents">.{rest}</span>
    </span>
  )
}
