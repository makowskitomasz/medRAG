export function formatDistanceToNow(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60) return "przed chwilą"
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin} min temu`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} godz. temu`
  const diffD = Math.floor(diffH / 24)
  if (diffD < 30) return `${diffD} dni temu`
  const diffM = Math.floor(diffD / 30)
  if (diffM < 12) return `${diffM} mies. temu`
  return `${Math.floor(diffM / 12)} lat temu`
}
