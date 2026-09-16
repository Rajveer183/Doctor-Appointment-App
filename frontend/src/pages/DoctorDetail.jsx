import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { format, startOfDay } from 'date-fns'
import { fetchDoctor, fetchDoctorSlots } from '../api/doctors'
import { bookAppointment } from '../api/appointments'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import DateStrip from '../components/DateStrip'
import SlotGrid from '../components/SlotGrid'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { Skeleton, SlotGridSkeleton } from '../components/ui/Skeleton'
import ErrorState from '../components/ui/ErrorState'

export default function DoctorDetail() {
  const { doctorId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  const { patientId } = useIdentity()

  const [selectedDate, setSelectedDate] = useState(startOfDay(new Date()))
  const [selectedSlotId, setSelectedSlotId] = useState(null)
  const { register, handleSubmit, reset } = useForm({ defaultValues: { reason: '' } })

  const {
    data: doctor,
    isLoading: doctorLoading,
    isError: doctorError,
    error: doctorErrorObj,
    refetch: refetchDoctor,
  } = useQuery({ queryKey: ['doctor', doctorId], queryFn: () => fetchDoctor(doctorId) })

  const dateKey = format(selectedDate, 'yyyy-MM-dd')
  const {
    data: slots,
    isLoading: slotsLoading,
    isError: slotsError,
    refetch: refetchSlots,
  } = useQuery({
    queryKey: ['slots', doctorId, dateKey, patientId],
    queryFn: () => fetchDoctorSlots(doctorId, { date: dateKey, patientId }),
    enabled: !!doctorId,
  })

  const bookMutation = useMutation({
    mutationFn: bookAppointment,
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: ['patientAppointments', patientId] })
      navigate(`/appointments/confirmation/${appointment.id}`, { state: appointment })
    },
    onError: (err) => {
      toast(err.message, 'error')
      setSelectedSlotId(null)
      refetchSlots()
    },
  })

  function onSubmit(values) {
    if (!selectedSlotId) {
      toast('Please pick a time slot first.', 'error')
      return
    }
    if (!patientId) {
      toast('Select a patient profile from the top bar first.', 'error')
      return
    }
    bookMutation.mutate({ slotId: selectedSlotId, patientId, reason: values.reason })
  }

  if (doctorLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-10 w-full" />
        <SlotGridSkeleton />
      </div>
    )
  }

  if (doctorError) {
    return <ErrorState message={doctorErrorObj.message} onRetry={refetchDoctor} />
  }

  return (
    <div className="animate-fade-in space-y-6">
      <Card className="flex items-start gap-4">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xl font-semibold text-brand-700">
          {doctor.name
            .replace('Dr. ', '')
            .split(' ')
            .map((n) => n[0])
            .join('')}
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-900">{doctor.name}</h1>
          <p className="text-sm text-slate-500">
            {doctor.specialty} · {doctor.experience_years} years experience
          </p>
          <p className="mt-2 text-sm text-slate-600">{doctor.bio}</p>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-slate-800">Pick a date</h2>
        <div className="mt-3">
          <DateStrip
            selectedDate={selectedDate}
            onSelect={(d) => {
              setSelectedDate(d)
              setSelectedSlotId(null)
            }}
          />
        </div>

        <h2 className="mt-6 text-sm font-semibold text-slate-800">Available times</h2>
        <div className="mt-3">
          {slotsLoading && <SlotGridSkeleton />}
          {slotsError && <ErrorState message="Couldn't load slots." onRetry={refetchSlots} />}
          {!slotsLoading && !slotsError && (
            <SlotGrid slots={slots} selectedSlotId={selectedSlotId} onSelect={setSelectedSlotId} />
          )}
        </div>
      </Card>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)}>
          <label className="text-sm font-semibold text-slate-800" htmlFor="reason">
            Reason for visit (optional)
          </label>
          <textarea
            id="reason"
            {...register('reason')}
            rows={3}
            placeholder="Briefly describe your symptoms or reason for the visit"
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <Button
            type="submit"
            className="mt-4 w-full sm:w-auto"
            loading={bookMutation.isPending}
            disabled={!selectedSlotId}
          >
            Confirm Booking
          </Button>
        </form>
      </Card>
    </div>
  )
}
