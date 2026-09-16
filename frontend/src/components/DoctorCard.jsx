import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import Card from './ui/Card'
import Badge from './ui/Badge'
import Button from './ui/Button'

export default function DoctorCard({ doctor, matchReason }) {
  const navigate = useNavigate()

  return (
    <Card hoverable className="animate-scale-in flex flex-col">
      <div className="flex items-start gap-3">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand-100 text-lg font-semibold text-brand-700">
          {doctor.name
            .replace('Dr. ', '')
            .split(' ')
            .map((n) => n[0])
            .join('')}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-slate-900">{doctor.name}</h3>
          <p className="text-xs text-slate-500">{doctor.specialty}</p>
          <p className="mt-0.5 text-xs text-slate-400">{doctor.experience_years} years experience</p>
        </div>
      </div>

      {matchReason && (
        <Badge color="brand" className="mt-3 w-fit">
          {matchReason}
        </Badge>
      )}

      <div className="mt-3 text-xs text-slate-500">
        {doctor.next_available_slot ? (
          <>
            Next available:{' '}
            <span className="font-medium text-slate-700">
              {format(new Date(doctor.next_available_slot), 'EEE, MMM d · h:mm a')}
            </span>
          </>
        ) : (
          'No upcoming slots'
        )}
      </div>

      <Button size="sm" className="mt-4 w-full" onClick={() => navigate(`/doctors/${doctor.id}`)}>
        View & Book
      </Button>
    </Card>
  )
}
