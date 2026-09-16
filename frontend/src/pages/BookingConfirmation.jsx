import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { fetchAppointment } from '../api/appointments'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { StatusBadge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import ErrorState from '../components/ui/ErrorState'

export default function BookingConfirmation() {
  const { appointmentId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const stateAppointment = location.state

  const {
    data: appointment,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['appointment', appointmentId],
    queryFn: () => fetchAppointment(appointmentId),
    initialData: stateAppointment,
  })

  if (isLoading && !appointment) return <Skeleton className="h-64 w-full" />
  if (isError) return <ErrorState message={error.message} onRetry={refetch} />
  if (!appointment) return null

  return (
    <div className="animate-fade-in mx-auto max-w-md">
      <div className="animate-scale-in flex flex-col items-center text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-3xl">✓</div>
        <h1 className="mt-4 text-xl font-bold text-slate-900">Appointment Confirmed</h1>
        <p className="mt-1 text-sm text-slate-500">A confirmation has been recorded for your visit.</p>
      </div>

      <Card className="mt-6 space-y-3">
        <Row label="Doctor" value={appointment.doctor.name} />
        <Row label="Specialty" value={appointment.doctor.specialty} />
        <Row
          label="Date & time"
          value={format(new Date(appointment.slot.start_datetime), 'EEEE, MMM d · h:mm a')}
        />
        <Row label="Patient" value={appointment.patient.name} />
        {appointment.reason && <Row label="Reason" value={appointment.reason} />}
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs font-medium text-slate-400">Status</span>
          <StatusBadge status={appointment.status} />
        </div>
      </Card>

      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        <Button className="flex-1" onClick={() => navigate('/appointments')}>
          View My Appointments
        </Button>
        <Button variant="secondary" className="flex-1" onClick={() => navigate('/doctors')}>
          Book Another
        </Button>
      </div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="shrink-0 text-slate-400">{label}</span>
      <span className="text-right font-medium text-slate-800">{value}</span>
    </div>
  )
}
