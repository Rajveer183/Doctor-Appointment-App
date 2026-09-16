import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
})

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail || 'Something went wrong. Please try again.'
    return Promise.reject(new Error(message))
  },
)
