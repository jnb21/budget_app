// Money is always integer cents, like the backend (never floats: 0.1 + 0.2 != 0.3).
// These helpers only turn cents into text and text into cents.

/** 147500 -> { negative: false, dollars: "1,475", cents: "00" } */
export function splitCents(cents) {
  const abs = Math.abs(cents)
  return {
    negative: cents < 0,
    dollars: Math.floor(abs / 100).toLocaleString('en-US'),
    cents: String(abs % 100).padStart(2, '0'),
  }
}

/** -5499 -> "−$54.99". With { plus: true }, positive amounts get a "+". */
export function formatMoney(cents, { plus = false } = {}) {
  const { negative, dollars, cents: rest } = splitCents(cents)
  const sign = negative ? '−' : plus && cents > 0 ? '+' : ''
  return `${sign}$${dollars}.${rest}`
}

/** Like formatMoney, but drops ".00": 3200 -> "$32", 3250 -> "$32.50". For chips and short labels. */
export function formatMoneyShort(cents) {
  const text = formatMoney(cents)
  return text.endsWith('.00') ? text.slice(0, -3) : text
}

/** 5499 -> "54.99": the value to put back in an amount field when editing. */
export function centsToInput(cents) {
  const { dollars, cents: rest } = splitCents(cents)
  return `${dollars.replaceAll(',', '')}.${rest}`
}

/**
 * What the user typed in an amount field -> cents, or null if it isn't an amount.
 * Accepts "12", "12.5", "12.50", "1,234.56", "$12", ".99". Never negative: the
 * expense/income switch decides the sign.
 */
export function parseAmount(text) {
  const cleaned = String(text).replace(/[\s$,]/g, '')
  const match = /^(\d*)(?:\.(\d{0,2}))?$/.exec(cleaned)
  if (!match || (match[1] === '' && !match[2])) return null
  const dollars = Number(match[1] || '0')
  const cents = Number((match[2] ?? '').padEnd(2, '0'))
  return dollars * 100 + cents
}

/** The class for a big headline amount: from $10,000 up it gets a smaller size so it fits beside the ring. */
export function heroFigureClass(cents) {
  return Math.abs(cents) >= 1_000_000 ? 'hero-figure hero-figure-long' : 'hero-figure'
}
