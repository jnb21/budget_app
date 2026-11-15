// Runs before every test file (see vite.config.js): undo whatever a test changed.
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup() // remove the rendered page
  vi.unstubAllGlobals() // put the real fetch back
  vi.useRealTimers() // undo a faked "today"
  localStorage.clear() // forget "welcome screen seen"
})
