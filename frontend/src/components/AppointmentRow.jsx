import { format, differenceInMinutes } from 'date-fns'
import Card from './ui/Card'
import { StatusBadge } from './ui/Badge'
import Button from './ui/Button'

// Mirrors app.config.settings.cancellation_window_minutes on the backend, which is the
// source of truth — this only drives the disabled/tooltip hint, the API enforces it for real.
const CANCELLATION_WINDOW_MINUTES = 60

export default function AppointmentRow({ appointment, onCancelClick, role = 'patient' }) {
  const start = new Date(appointment.slot.start_datetime)
  const withinWindow = differenceInMinutes(start, new Date()) < CANCELLATION_WINDOW_MINUTES
  const canCancel = appointment.status === 'confirmed' && !withinWindow

  return (
    <Card className="animate-slide-up flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-sm font-semibold text-slate-900">
            {role === 'patient' ? appointment.doctor.name : appointment.patient.name}
          </h3>
          <StatusBadge status={appointment.status} />
        </div>
        <p className="mt-0.5 text-xs text-slate-500">
          {role === 'patient' ? appointment.doctor.specialty : `Reason: ${appointment.reason || '—'}`}
        </p>
        <p className="mt-1 text-sm text-slate-700">{format(start, 'EEE, MMM d · h:mm a')}</p>
      </div>

      {role === 'patient' && appointment.status === 'confirmed' && (
        <div className="shrink-0" title={!canCancel ? `Cancellations must be made ${CANCELLATION_WINDOW_MINUTES} min in advance` : undefined}>
          <Button variant="danger" size="sm" disabled={!canCancel} onClick={() => onCancelClick(appointment)}>
            Cancel
          </Button>
        </div>
      )}
    </Card>
  )
}
