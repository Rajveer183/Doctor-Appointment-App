import { format } from 'date-fns'
import { StatusBadge } from '../ui/Badge'

export default function ToolResultCard({ event }) {
  switch (event.tool) {
    case 'search_doctors':
      return <DoctorListCard doctors={event.result} />
    case 'get_available_slots':
      return <SlotListCard slots={event.result} />
    case 'book_appointment':
      return <BookingResultCard result={event.result} />
    case 'cancel_appointment':
      return <CancelResultCard result={event.result} />
    case 'list_my_appointments':
      return <AppointmentListCard appointments={event.result} />
    default:
      return null
  }
}

function CardShell({ children }) {
  return <div className="animate-scale-in mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">{children}</div>
}

function DoctorListCard({ doctors }) {
  if (!doctors?.length) return <CardShell>No doctors found.</CardShell>
  return (
    <CardShell>
      <div className="space-y-2">
        {doctors.map((d) => (
          <div key={d.id} className="flex items-center justify-between">
            <div>
              <div className="font-semibold text-slate-800">{d.name}</div>
              <div className="text-slate-500">
                {d.specialty} · {d.experience_years} yrs
              </div>
            </div>
            {d.next_available_slot && (
              <div className="text-right text-slate-500">{format(new Date(d.next_available_slot), 'MMM d, h:mm a')}</div>
            )}
          </div>
        ))}
      </div>
    </CardShell>
  )
}

function SlotListCard({ slots }) {
  if (!slots?.length) return <CardShell>No open slots that day.</CardShell>
  return (
    <CardShell>
      <div className="flex flex-wrap gap-1.5">
        {slots.slice(0, 12).map((s) => (
          <span key={s.id} className="rounded-full bg-white px-2 py-1 font-medium text-slate-700 shadow-sm">
            {format(new Date(s.start_datetime), 'h:mm a')}
          </span>
        ))}
        {slots.length > 12 && <span className="px-2 py-1 text-slate-400">+{slots.length - 12} more</span>}
      </div>
    </CardShell>
  )
}

function BookingResultCard({ result }) {
  if (!result?.success) {
    return <CardShell><span className="text-red-600">Booking failed: {result?.error || 'unknown error'}</span></CardShell>
  }
  return (
    <CardShell>
      <div className="flex items-center gap-2 font-semibold text-green-700">✓ Appointment booked</div>
      <div className="mt-1 text-slate-600">
        {result.doctor} · {format(new Date(result.start_datetime), 'EEE, MMM d · h:mm a')}
      </div>
    </CardShell>
  )
}

function CancelResultCard({ result }) {
  if (!result?.success) {
    return <CardShell><span className="text-red-600">Cancel failed: {result?.error || 'unknown error'}</span></CardShell>
  }
  return <CardShell><span className="font-semibold text-slate-700">✓ Appointment #{result.appointment_id} cancelled</span></CardShell>
}

function AppointmentListCard({ appointments }) {
  if (!appointments?.length) return <CardShell>No appointments found.</CardShell>
  return (
    <CardShell>
      <div className="space-y-2">
        {appointments.map((a) => (
          <div key={a.id} className="flex items-center justify-between">
            <div>
              <div className="font-semibold text-slate-800">{a.doctor}</div>
              <div className="text-slate-500">{format(new Date(a.start_datetime), 'MMM d, h:mm a')}</div>
            </div>
            <StatusBadge status={a.status} />
          </div>
        ))}
      </div>
    </CardShell>
  )
}
