import axios from 'axios'

// In local dev this stays relative and Vite's /api proxy (vite.config.js) forwards it to
// the backend. In production there is no proxy — nginx serves static files only — so the
// build needs the real backend origin baked in via VITE_API_URL (see frontend/Dockerfile
// and commands.md step 8, `--build-arg VITE_API_URL=$BACKEND_URL`).
const baseURL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

export const apiClient = axios.create({ baseURL })

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail || 'Something went wrong. Please try again.'
    return Promise.reject(new Error(message))
  },
)
