import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPatients } from '../api/patients'
import { useIdentity } from '../context/IdentityContext'

// Defaults the switcher to the first available option once data loads, without
// fighting a value the person already picked.
function useDefaultSelection(list, current, setCurrent) {
  useEffect(() => {
    if (!current && list.length > 0) setCurrent(list[0].id)
  }, [list, current, setCurrent])
}

export function PatientSwitcher() {
  const { patientId, setPatientId } = useIdentity()
  const { data: patients = [] } = useQuery({ queryKey: ['patients'], queryFn: fetchPatients })
  useDefaultSelection(patients, patientId, setPatientId)

  return (
    <select
      value={patientId ?? ''}
      onChange={(e) => setPatientId(Number(e.target.value))}
      className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
      aria-label="Booking as patient"
    >
      {patients.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  )
}
