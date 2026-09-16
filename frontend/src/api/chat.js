import { apiClient } from './client'

export async function sendChatMessage({ message, conversationHistory, patientId }) {
  const { data } = await apiClient.post('/chat', {
    message,
    conversation_history: conversationHistory,
    patient_id: patientId,
  })
  return data
}
