// The password rules, shown live on the sign-up form. The backend checks the
// same rules (backend/app/services/auth_service.py): this copy only gives a
// quicker answer, since anyone can skip the browser.
//
// Length matters most, so the rules favor passphrases ("correct horse
// battery") over symbol puzzles. Any character is accepted.

export const MIN_PASSWORD = 10
export const MAX_PASSWORD = 128

// Long enough for the length rule, yet guessed first by every attacker.
const COMMON = new Set([
  '1234567890', '12345678910', '0123456789', '1q2w3e4r5t', '1qaz2wsx3edc',
  'qwertyuiop', 'qwerty1234', 'qwerty12345', 'asdfghjkl1', 'zxcvbnm123',
  'password12', 'password123', 'password1!', 'passw0rd123', 'p@ssw0rd123',
  'iloveyou12', 'iloveyou123', 'welcome123', 'letmein123', 'abc1234567',
  'abcdefghij', 'admin12345', 'football123', 'baseball123', 'sunshine12',
  'princess12', 'monkey12345', 'dragon12345', 'trustno1234', 'changeme123',
])

const isLetter = (ch) => /\p{L}/u.test(ch)
const chars = (text) => [...text] // by character, so an emoji counts once

/** Each rule: what it says on screen, and whether `password` passes it. */
export const PASSWORD_RULES = [
  {
    id: 'length',
    label: `${MIN_PASSWORD} to ${MAX_PASSWORD} characters`,
    passes: (password) => chars(password).length >= MIN_PASSWORD && chars(password).length <= MAX_PASSWORD,
  },
  {
    id: 'letter',
    label: 'At least one letter',
    passes: (password) => chars(password).some(isLetter),
  },
  {
    id: 'other',
    label: 'At least one number, symbol or space',
    passes: (password) => chars(password).some((ch) => !isLetter(ch)),
  },
  {
    id: 'common',
    label: 'Not a common password',
    passes: (password) => password.length > 0 && !COMMON.has(password.toLowerCase()),
  },
  {
    id: 'email',
    label: 'Not your email',
    passes: (password, email) => password.length > 0 && password.trim().toLowerCase() !== email.trim().toLowerCase(),
  },
]

/** The rules `password` breaks (empty = good to go). */
export function brokenRules(password, email = '') {
  return PASSWORD_RULES.filter((rule) => !rule.passes(password, email))
}
