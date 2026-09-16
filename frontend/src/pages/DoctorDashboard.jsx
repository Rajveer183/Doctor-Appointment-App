import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { addDays, format, isToday, subDays } from 'date-fns'
import { fetchDoctorSchedule } from '../api/doctors'
import { updateAppointmentStatus } from '../api/appointments'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { StatusBadge } from '../components/ui/Badge'
import { ListRowSkeleton } from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'

export default function DoctorDashboard() {
  const { doctorId } = useIdentity()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [date, setDate] = useState(new Date())
  const dateKey = format(date, 'yyyy-MM-dd')

  const {
    data: appointments,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['doctorSchedule', doctorId, dateKey],
    queryFn: () => fetchDoctorSchedule(doctorId, dateKey),
    enabled: !!doctorId,
  })

  const statusMutation = useMutation({
    mutationFn: ({ appointmentId, status }) => updateAppointmentStatus(appointmentId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctorSchedule', doctorId, dateKey] })
    },
    onError: (err) => toast(err.message, 'error'),
  })

  if (!doctorId) {
    return <EmptyState icon="🩺" title="Pick a doctor" description="Choose a doctor profile from the top bar to see their schedule." />
  }

  return (
    <div className="animate-fade-in space-y-5">
      <h1 className="text-xl font-bold text-slate-900">Doctor Dashboard</h1>

      <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
        <Button variant="ghost" size="sm" onClick={() => setDate((d) => subDays(d, 1))}>
          ← Prev
        </Button>
        <div className="text-sm font-semibold text-slate-800">
          {format(date, 'EEEE, MMM d')} {isToday(date) && <span className="text-brand-600">(Today)</span>}
        </div>
        <Button variant="ghost" size="sm" onClick={() => setDate((d) => addDays(d, 1))}>
          Next →
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <ListRowSkeleton key={i} />
          ))}
        </div>
      )}

      {isError && <ErrorState message={error.message} onRetry={refetch} />}

      {!isLoading && !isError && appointments?.length === 0 && (
        <EmptyState icon="✅" title="No appointments scheduled" description="Nothing on the books for this day." />
      )}

      {!isLoading && !isError && appointments?.length > 0 && (
        <div className="space-y-3">
          {appointments.map((appt) => (
            <Card key={appt.id} className="animate-slide-up flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">{appt.patient.name}</h3>
                  <StatusBadge status={appt.status} />
                </div>
                <p className="mt-0.5 text-xs text-slate-500">{appt.reason || 'No reason provided'}</p>
                <p className="mt-1 text-sm text-slate-700">{format(new Date(appt.slot.start_datetime), 'h:mm a')}</p>
              </div>

              {appt.status === 'confirmed' && (
                <div className="flex shrink-0 gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ appointmentId: appt.id, status: 'completed' })}
                  >
                    Mark Complete
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    loading={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ appointmentId: appt.id, status: 'no_show' })}
                  >
                    No-show
                  </Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
