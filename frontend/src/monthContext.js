import { createContext, useContext } from 'react'

// The month every page shows. One shared value, so switching pages keeps the
// month you picked. MonthProvider (MonthProvider.jsx) holds it.
export const MonthContext = createContext(null)

/** { month: "2026-11", setMonth } */
export function useMonth() {
  const value = useContext(MonthContext)
  if (!value) throw new Error('useMonth() needs a <MonthProvider> above it')
  return value
}
