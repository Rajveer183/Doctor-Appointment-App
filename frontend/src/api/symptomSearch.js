import { apiClient } from './client'

export async function searchSymptom(text) {
  const { data } = await apiClient.post('/symptom-search', { text })
  return data
}
