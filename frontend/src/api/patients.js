import { apiClient } from './client'

export async function fetchPatients() {
  const { data } = await apiClient.get('/patients')
  return data
}

export async function fetchPatientAppointments(patientId, { upcoming } = {}) {
  const { data } = await apiClient.get(`/patients/${patientId}/appointments`, { params: { upcoming } })
  return data
}
