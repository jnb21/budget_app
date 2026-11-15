// Every call to the backend goes through this file, so components never deal
// with URLs or HTTP status codes themselves (like routers vs. services).

/**
 * Ask the backend for its health.
 * Resolves to { status: "ok" | "degraded", database: "ok" | "unavailable" }.
 * Throws if the backend can't be reached or answers something unexpected.
 */
export async function getHealth() {
  const response = await fetch('/health') // throws by itself if there is no network at all
  // 200 = healthy, 503 = up but degraded. Both carry the JSON body we expect.
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`Unexpected status ${response.status}`)
  }
  return response.json()
}
