import { NavLink, Outlet, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { PatientSwitcher, DoctorSwitcher } from './IdentitySwitcher'
import ChatWidget from './chat/ChatWidget'

const NAV_LINKS = [
  { to: '/', label: 'Home' },
  { to: '/doctors', label: 'Find a Doctor' },
  { to: '/appointments', label: 'My Appointments' },
  { to: '/dashboard', label: 'Doctor Dashboard' },
]

export default function Layout() {
  const location = useLocation()
  const isDashboard = location.pathname.startsWith('/dashboard')

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <NavLink to="/" className="text-lg font-bold text-brand-700">
            CarePoint
          </NavLink>
          <nav className="hidden gap-1 sm:flex">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  clsx(
                    'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100',
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {isDashboard ? <DoctorSwitcher /> : <PatientSwitcher />}
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-slate-100 px-4 py-2 sm:hidden">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                clsx(
                  'whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium',
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600',
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>

      <ChatWidget />
    </div>
  )
}
