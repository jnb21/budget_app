// Months as the API uses them: "2026-11". Dates as the API uses them: "2026-11-14".
// Dates are read as LOCAL days: new Date("2026-11-14") would be midnight UTC,
// which is still Nov 13 in Montreal.

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const pad = (n) => String(n).padStart(2, '0')

/** The month containing `today`: "2026-11". */
export function currentMonth(today = new Date()) {
  return `${today.getFullYear()}-${pad(today.getMonth() + 1)}`
}

/** shiftMonth("2026-01", -1) -> "2025-12" */
export function shiftMonth(month, delta) {
  const [year, m] = month.split('-').map(Number)
  const index = year * 12 + (m - 1) + delta
  return `${Math.floor(index / 12)}-${pad((index % 12) + 1)}`
}

/** "2026-11" -> "November" */
export function monthName(month) {
  return MONTH_NAMES[Number(month.split('-')[1]) - 1]
}

/** "2026-11" -> "Nov" */
export function shortMonthName(month) {
  return monthName(month).slice(0, 3)
}

/** "2026-11" -> "November 2026" */
export function monthLabel(month) {
  return `${monthName(month)} ${month.split('-')[0]}`
}

/** "2026-11-14" -> a Date at local midnight on that day. */
export function parseDay(isoDate) {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** A Date -> "2026-11-14" (local day). */
export function toIsoDay(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** "2026-11-14" -> "Sat, Nov 14" */
export function formatDay(isoDate) {
  const date = parseDay(isoDate)
  return `${DAY_NAMES[date.getDay()]}, ${MONTH_NAMES[date.getMonth()].slice(0, 3)} ${date.getDate()}`
}

/** "2026-11-14" -> "Nov 14" */
export function formatShortDay(isoDate) {
  const date = parseDay(isoDate)
  return `${MONTH_NAMES[date.getMonth()].slice(0, 3)} ${date.getDate()}`
}

/** The date a new transaction starts with: today if it's in `month`, else that month's 1st. */
export function defaultDayFor(month, today = new Date()) {
  return currentMonth(today) === month ? toIsoDay(today) : `${month}-01`
}
