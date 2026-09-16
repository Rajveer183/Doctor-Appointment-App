import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { fetchPatientAppointments } from '../api/patients'
import { cancelAppointment } from '../api/appointments'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import AppointmentRow from '../components/AppointmentRow'
import { ListRowSkeleton } from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'

export default function MyAppointments() {
  const { patientId } = useIdentity()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState('upcoming')
  const [pendingCancel, setPendingCancel] = useState(null)

  const upcoming = tab === 'upcoming'
  const {
    data: appointments,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['patientAppointments', patientId, upcoming],
    queryFn: () => fetchPatientAppointments(patientId, { upcoming }),
    enabled: !!patientId,
  })

  const cancelMutation = useMutation({
    mutationFn: cancelAppointment,
    onSuccess: () => {
      toast('Appointment cancelled.')
      queryClient.invalidateQueries({ queryKey: ['patientAppointments', patientId] })
      setPendingCancel(null)
    },
    onError: (err) => {
      toast(err.message, 'error')
      setPendingCancel(null)
    },
  })

  return (
    <div className="animate-fade-in space-y-5">
      <h1 className="text-xl font-bold text-slate-900">My Appointments</h1>

      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
        {['upcoming', 'past'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              'rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-colors',
              tab === t ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500',
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {!patientId && (
        <EmptyState icon="👤" title="Pick a patient" description="Choose a patient profile from the top bar to see appointments." />
      )}

      {patientId && isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <ListRowSkeleton key={i} />
          ))}
        </div>
      )}

      {patientId && isError && <ErrorState message={error.message} onRetry={refetch} />}

      {patientId && !isLoading && !isError && appointments?.length === 0 && (
        <EmptyState
          icon="🗓️"
          title={upcoming ? 'No upcoming appointments' : 'No past appointments'}
          description={upcoming ? 'Book a visit with a doctor to see it here.' : ''}
          action={
            upcoming && (
              <Button size="sm" onClick={() => navigate('/doctors')}>
                Find a Doctor
              </Button>
            )
          }
        />
      )}

      {patientId && !isLoading && !isError && appointments?.length > 0 && (
        <div className="space-y-3">
          {appointments.map((appt) => (
            <AppointmentRow key={appt.id} appointment={appt} onCancelClick={setPendingCancel} />
          ))}
        </div>
      )}

      <Modal
        open={!!pendingCancel}
        onClose={() => setPendingCancel(null)}
        title="Cancel this appointment?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setPendingCancel(null)}>
              Keep it
            </Button>
            <Button variant="danger" loading={cancelMutation.isPending} onClick={() => cancelMutation.mutate(pendingCancel.id)}>
              Yes, cancel
            </Button>
          </>
        }
      >
        {pendingCancel && (
          <p>
            This will cancel your appointment with <strong>{pendingCancel.doctor.name}</strong> on{' '}
            <strong>{new Date(pendingCancel.slot.start_datetime).toLocaleString()}</strong>. This can't be undone.
          </p>
        )}
      </Modal>
    </div>
  )
}
