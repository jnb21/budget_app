import { useMemo, useState } from 'react'
import { MonthContext } from './monthContext.js'
import { currentMonth } from './months.js'

/** Holds the shared month. Tests pass `initialMonth` so they don't depend on today's date. */
export default function MonthProvider({ initialMonth, children }) {
  const [month, setMonth] = useState(() => initialMonth ?? currentMonth())
  const value = useMemo(() => ({ month, setMonth }), [month])
  return <MonthContext.Provider value={value}>{children}</MonthContext.Provider>
}
