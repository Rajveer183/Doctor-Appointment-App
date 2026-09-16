import { createContext, useCallback, useContext, useState } from 'react'
import { createPortal } from 'react-dom'
import clsx from 'clsx'

const ToastContext = createContext(null)

let idCounter = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (message, type = 'success') => {
      const id = ++idCounter
      setToasts((prev) => [...prev, { id, message, type }])
      setTimeout(() => dismiss(id), 4000)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {createPortal(
        <div className="fixed inset-x-0 bottom-4 z-[100] flex flex-col items-center gap-2 px-4 sm:bottom-6 sm:items-end sm:right-6 sm:left-auto">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={clsx(
                'animate-slide-up w-full max-w-sm rounded-lg px-4 py-3 text-sm font-medium shadow-lg sm:w-auto',
                t.type === 'success' && 'bg-slate-900 text-white',
                t.type === 'error' && 'bg-red-600 text-white',
              )}
            >
              {t.message}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
