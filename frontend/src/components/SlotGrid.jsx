import { format } from 'date-fns'
import clsx from 'clsx'
import EmptyState from './ui/EmptyState'

export default function SlotGrid({ slots, selectedSlotId, onSelect }) {
  if (slots.length === 0) {
    return (
      <EmptyState
        icon="🗓️"
        title="No open slots on this day"
        description="Try picking a different date from the strip above."
      />
    )
  }

  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
      {slots.map((slot) => {
        const active = slot.id === selectedSlotId
        return (
          <button
            key={slot.id}
            onClick={() => onSelect(slot.id)}
            className={clsx(
              'relative rounded-lg border px-2 py-2.5 text-xs font-medium transition-all duration-150',
              active
                ? 'scale-[1.03] border-brand-600 bg-brand-600 text-white shadow-sm'
                : 'border-slate-200 bg-white text-slate-700 hover:border-brand-400 hover:bg-brand-50',
            )}
          >
            {slot.recommended && (
              <span className="absolute -top-2 left-1/2 -translate-x-1/2 rounded-full bg-amber-400 px-1.5 py-0.5 text-[9px] font-semibold text-amber-900">
                Best fit
              </span>
            )}
            {format(new Date(slot.start_datetime), 'h:mm a')}
          </button>
        )
      })}
    </div>
  )
}
