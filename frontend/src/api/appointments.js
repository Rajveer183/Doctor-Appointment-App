import { apiClient } from './client'

export async function bookAppointment({ slotId, patientId, reason }) {
  const { data } = await apiClient.post('/appointments', { slot_id: slotId, patient_id: patientId, reason })
  return data
}

export async function fetchAppointment(appointmentId) {
  const { data } = await apiClient.get(`/appointments/${appointmentId}`)
  return data
}

export async function cancelAppointment(appointmentId) {
  const { data } = await apiClient.patch(`/appointments/${appointmentId}/cancel`)
  return data
}

export async function updateAppointmentStatus(appointmentId, status) {
  const { data } = await apiClient.patch(`/appointments/${appointmentId}/status`, { status })
  return data
}
