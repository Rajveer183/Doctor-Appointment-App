import { apiClient } from './client'

export async function fetchSpecialties() {
  const { data } = await apiClient.get('/specialties')
  return data
}

export async function fetchDoctors({ specialty } = {}) {
  const { data } = await apiClient.get('/doctors', { params: { specialty } })
  return data
}

export async function fetchDoctor(doctorId) {
  const { data } = await apiClient.get(`/doctors/${doctorId}`)
  return data
}

export async function fetchDoctorSlots(doctorId, { date, patientId } = {}) {
  const { data } = await apiClient.get(`/doctors/${doctorId}/slots`, {
    params: { date, patient_id: patientId },
  })
  return data
}

export async function fetchDoctorSchedule(doctorId, date) {
  const { data } = await apiClient.get(`/doctors/${doctorId}/schedule`, { params: { day: date } })
  return data
}
