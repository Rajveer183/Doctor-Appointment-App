import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import DoctorListing from './pages/DoctorListing'
import DoctorDetail from './pages/DoctorDetail'
import BookingConfirmation from './pages/BookingConfirmation'
import MyAppointments from './pages/MyAppointments'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/doctors" element={<DoctorListing />} />
        <Route path="/doctors/:doctorId" element={<DoctorDetail />} />
        <Route path="/appointments/confirmation/:appointmentId" element={<BookingConfirmation />} />
        <Route path="/appointments" element={<MyAppointments />} />
      </Route>
    </Routes>
  )
}
