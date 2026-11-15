// A stand-in for the browser's fetch that answers like the backend, by
// "METHOD /url", so page tests run without a backend and can test every state
// (empty month, errors, 422s) in milliseconds.

import { vi } from 'vitest'

const REPLY = Symbol('reply')

/** An answer with a status other than 200: reply(422, { detail: "..." }), reply(204). */
export function reply(status, body = null) {
  return { [REPLY]: true, status, body }
}

/**
 * Replace fetch with a fake that answers from `routes`:
 *   { "GET /api/categories": [...], "POST /api/transactions": reply(201, {...}) }
 * A plain value is a 200 with that JSON body. A function gets the request's
 * parsed body and returns the answer. An Error is thrown, like fetch does when
 * nothing answers. A request with no route answers 404, so a test fails loudly.
 * Tests can change `routes` midway, e.g. to answer the reload after a save.
 */
export function fakeApi(routes) {
  const fetch = vi.fn(async (url, options = {}) => {
    const key = `${options.method ?? 'GET'} ${url}`
    if (!(key in routes)) return { status: 404, json: async () => ({ detail: `no fake answer for ${key}` }) }
    let answer = routes[key]
    if (typeof answer === 'function') answer = answer(options.body ? JSON.parse(options.body) : undefined)
    if (answer instanceof Error) throw answer
    const { status, body } = answer?.[REPLY] ? answer : { status: 200, body: answer }
    return { status, json: async () => structuredClone(body) }
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

/** The bodies sent with one kind of request, parsed: sent(fetch, "PUT /api/budgets") -> [{...}] */
export function sent(fetch, key) {
  return fetch.mock.calls
    .filter(([url, options = {}]) => `${options.method ?? 'GET'} ${url}` === key)
    .map(([, options]) => (options?.body ? JSON.parse(options.body) : undefined))
}
