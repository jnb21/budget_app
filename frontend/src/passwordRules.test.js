// Unit tests for the password rules shown on the sign-up form.
// Risk covered: the form saying "OK" to a password the backend refuses (or the
// reverse), and rejecting good passphrases or non-English characters.

import { expect, test } from 'vitest'
import { brokenRules } from './passwordRules.js'

const broken = (password, email = 'alice@example.com') => brokenRules(password, email).map((r) => r.id)

test.each([
  'abcdefgh12',            // exactly 10
  'a'.repeat(127) + '1',   // exactly 128
  'correct horse battery', // a passphrase: the spaces count
  'mot de passe très sûr', // accents
  'пароль-надёжный',       // any alphabet
  'ab😀cdefghij',           // an emoji is one character, and counts as a symbol
])('%j passes every rule', (password) => {
  expect(broken(password)).toEqual([])
})

test.each([
  ['abcdefgh1', ['length']],                 // 9: one short
  ['a'.repeat(128) + '1', ['length']],       // 129: one over
  ['abcdefghijk', ['other']],                // letters only
  ['1234567890!', ['letter']],               // no letter
  ['Password123', ['common']],               // capitals don't help
  ['alice@example.com', ['email']],
  ['', ['length', 'letter', 'other', 'common', 'email']],
])('%j breaks %j', (password, rules) => {
  expect(broken(password)).toEqual(rules)
})

test('an emoji counts as one character, like the backend counts it', () => {
  expect(broken('😀'.repeat(9) + 'a')).toEqual([]) // 10 characters, even though it's 19 UTF-16 units
})
