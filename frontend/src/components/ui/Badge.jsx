import clsx from 'clsx'

export default function Badge({ className, children, color = 'slate' }) {
  const colorMap = {
    slate: 'bg-slate-100 text-slate-600',
    brand: 'bg-brand-100 text-brand-700',
    green: 'bg-green-100 text-green-700',
    red: 'bg-red-100 text-red-700',
    amber: 'bg-amber-100 text-amber-700',
  }
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
        colorMap[color],
        className,
      )}
    >
      {children}
    </span>
  )
}

const STATUS_STYLES = {
  confirmed: 'bg-status-confirmed-bg text-status-confirmed-text',
  completed: 'bg-status-completed-bg text-status-completed-text',
  cancelled: 'bg-status-cancelled-bg text-status-cancelled-text',
  no_show: 'bg-status-noshow-bg text-status-noshow-text',
}

const STATUS_LABELS = {
  confirmed: 'Confirmed',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No-show',
}

export function StatusBadge({ status, className }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
        STATUS_STYLES[status] ?? STATUS_STYLES.cancelled,
        className,
      )}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}
