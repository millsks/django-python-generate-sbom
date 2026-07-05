// Human-format a duration in seconds for the History table (Story 6.3):
// '—' when unknown/negative, '450ms', '45s', '1m 23s', '2h 05m'.
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return '—'
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60)
    const s = Math.round(seconds % 60)
    return `${m}m ${s}s`
  }
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${String(m).padStart(2, '0')}m`
}
