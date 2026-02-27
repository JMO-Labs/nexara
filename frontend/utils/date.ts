/**
 * @file utils/date.ts
 * @brief Date formatting helpers for the Nexara frontend.
 *
 * Provides relative time display ("2 hours ago") and absolute
 * formatting for timestamps returned by the API.
 */

/**
 * @brief Format an ISO date string as a relative time string.
 * @param iso - ISO 8601 date string from the API.
 * @returns Human-readable relative time (e.g., "5 minutes ago").
 */
export function timeAgo(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (seconds < 60) return 'just now'

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/**
 * @brief Format an ISO date string for display.
 * @param iso - ISO 8601 date string.
 * @returns Formatted date string.
 */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
