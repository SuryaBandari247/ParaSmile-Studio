import type { ProjectStatus, JobStatus, TopicStatus } from '@/types'

type BadgeStatus = ProjectStatus | JobStatus | TopicStatus | string

const colors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-700',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  REVIEW: 'bg-yellow-100 text-yellow-700',
  RENDERED: 'bg-green-100 text-green-700',
  PUBLISHED: 'bg-purple-100 text-purple-700',
  PENDING: 'bg-gray-100 text-gray-600',
  RUNNING: 'bg-blue-100 text-blue-700',
  COMPLETED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  SELECTED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  SYNTHESIZED: 'bg-green-100 text-green-700',
  UPLOADED: 'bg-teal-100 text-teal-700',
  QUEUED: 'bg-yellow-100 text-yellow-700',
  SPLITTING: 'bg-blue-100 text-blue-700',
}

export function StatusBadge({ status }: { status: BadgeStatus }) {
  const cls = colors[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace('_', ' ')}
    </span>
  )
}
