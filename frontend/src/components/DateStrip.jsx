import { addDays, format, isSameDay, startOfDay } from 'date-fns'
import clsx from 'clsx'

export default function DateStrip({ selectedDate, onSelect, days = 14 }) {
  const today = startOfDay(new Date())
  const dates = Array.from({ length: days }, (_, i) => addDays(today, i))

  return (
    <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
      {dates.map((date) => {
        const active = isSameDay(date, selectedDate)
        return (
          <button
            key={date.toISOString()}
            onClick={() => onSelect(date)}
            className={clsx(
              'flex shrink-0 flex-col items-center rounded-xl border px-3.5 py-2 transition-colors duration-150',
              active
                ? 'border-brand-600 bg-brand-600 text-white'
                : 'border-slate-200 bg-white text-slate-600 hover:border-brand-300',
            )}
          >
            <span className="text-[10px] font-medium uppercase opacity-80">{format(date, 'EEE')}</span>
            <span className="text-sm font-semibold">{format(date, 'd')}</span>
            <span className="text-[10px] opacity-70">{format(date, 'MMM')}</span>
          </button>
        )
      })}
    </div>
  )
}
