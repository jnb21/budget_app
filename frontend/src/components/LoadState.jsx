import { Link } from 'react-router'

/** What a page shows while its data loads, or when loading failed. */
export default function LoadState({ status, error, onRetry }) {
  if (status === 'loading') {
    return (
      <div className="load-state" role="status">
        <span className="spinner" aria-hidden="true" />
        Loading…
      </div>
    )
  }
  return (
    <div className="card load-state load-error" role="alert">
      <p>{error?.message ?? 'Something went wrong.'}</p>
      <div className="load-error-actions">
        <button type="button" className="button button-primary" onClick={onRetry}>
          Try again
        </button>
        <Link to="/status" className="button">
          Check backend status
        </Link>
      </div>
    </div>
  )
}
