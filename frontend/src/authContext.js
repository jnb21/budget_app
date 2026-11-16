import { createContext, useContext } from 'react'

/** Who is logged in, plus logIn / signUp / logOut. Provided by AuthProvider. */
export const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

/** "alice.martin@example.com" -> "AM", "bob@example.com" -> "BO" */
export function initials(email) {
  const name = email.split('@')[0]
  const parts = name.split(/[._-]+/).filter(Boolean)
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)
  return letters.toUpperCase()
}
