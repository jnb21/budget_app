/**
 * What was spent from the 1st through day `lastDay` of a month, counted like the
 * dashboard: each category's net outflow, so a $25 refund lowers its category,
 * and a category where more came in than went out (like Income) counts as zero.
 * `transactions` are one month's, as GET /api/transactions returns them.
 */
export function spentThrough(transactions, lastDay) {
  const netByCategory = new Map()
  for (const t of transactions) {
    if (Number(t.posted_date.slice(8, 10)) > lastDay) continue
    const key = t.category_id ?? 'uncategorized'
    netByCategory.set(key, (netByCategory.get(key) ?? 0) + t.amount_cents)
  }
  let spent = 0
  for (const net of netByCategory.values()) if (net < 0) spent -= net
  return spent
}
