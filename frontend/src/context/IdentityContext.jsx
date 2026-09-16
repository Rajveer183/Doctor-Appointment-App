import { createContext, useContext, useEffect, useState } from 'react'

const IdentityContext = createContext(null)

function readStored(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? Number(raw) : null
  } catch {
    return null
  }
}

export function IdentityProvider({ children }) {
  const [patientId, setPatientIdState] = useState(() => readStored('patientId'))
  const [doctorId, setDoctorIdState] = useState(() => readStored('doctorId'))

  useEffect(() => {
    try {
      if (patientId) localStorage.setItem('patientId', String(patientId))
    } catch {
      /* private-window / blocked storage: identity just won't persist across reloads */
    }
  }, [patientId])

  useEffect(() => {
    try {
      if (doctorId) localStorage.setItem('doctorId', String(doctorId))
    } catch {
      /* same as above */
    }
  }, [doctorId])

  return (
    <IdentityContext.Provider
      value={{ patientId, setPatientId: setPatientIdState, doctorId, setDoctorId: setDoctorIdState }}
    >
      {children}
    </IdentityContext.Provider>
  )
}

export function useIdentity() {
  const ctx = useContext(IdentityContext)
  if (!ctx) throw new Error('useIdentity must be used within IdentityProvider')
  return ctx
}
