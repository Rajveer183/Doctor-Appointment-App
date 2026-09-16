import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { fetchDoctors, fetchSpecialties } from '../api/doctors'
import DoctorCard from '../components/DoctorCard'
import { DoctorCardSkeleton } from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'

export default function DoctorListing() {
  const [searchParams, setSearchParams] = useSearchParams()
  const specialty = searchParams.get('specialty') || ''
  const matchReason = searchParams.get('matchReason') || ''

  const { data: specialties = [] } = useQuery({ queryKey: ['specialties'], queryFn: fetchSpecialties })
  const {
    data: doctors,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['doctors', specialty],
    queryFn: () => fetchDoctors({ specialty: specialty || undefined }),
  })

  function setSpecialty(next) {
    const params = new URLSearchParams(searchParams)
    if (next) params.set('specialty', next)
    else params.delete('specialty')
    params.delete('matchReason')
    setSearchParams(params)
  }

  return (
    <div className="animate-fade-in space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Find a Doctor</h1>
        {matchReason && <p className="mt-1 text-sm text-brand-600">{matchReason}</p>}
      </div>

      <div className="flex flex-wrap gap-2 overflow-x-auto pb-1">
        <FilterChip label="All" active={!specialty} onClick={() => setSpecialty('')} />
        {specialties.map((s) => (
          <FilterChip key={s} label={s} active={specialty === s} onClick={() => setSpecialty(s)} />
        ))}
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <DoctorCardSkeleton key={i} />
          ))}
        </div>
      )}

      {isError && <ErrorState message={error.message} onRetry={refetch} />}

      {!isLoading && !isError && doctors?.length === 0 && (
        <EmptyState
          icon="🔍"
          title="No doctors found"
          description="Try a different specialty, or browse all doctors."
          action={
            <button onClick={() => setSpecialty('')} className="text-sm font-medium text-brand-600 underline">
              Clear filter
            </button>
          }
        />
      )}

      {!isLoading && !isError && doctors?.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {doctors.map((doctor) => (
            <DoctorCard key={doctor.id} doctor={doctor} matchReason={matchReason ? 'Matched to your symptoms' : null} />
          ))}
        </div>
      )}
    </div>
  )
}

function FilterChip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'whitespace-nowrap rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'border-brand-600 bg-brand-600 text-white'
          : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
      )}
    >
      {label}
    </button>
  )
}
