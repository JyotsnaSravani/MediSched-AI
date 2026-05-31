import { Routes, Route, Navigate } from 'react-router-dom'
import SimpleLayout from './components/SimpleLayout'
import StandaloneLoginPage from './pages/StandaloneLoginPage'
import SimpleDashboard from './pages/SimpleDashboard'
import PatientsPage from './pages/PatientsPage'
import DoctorsPage from './pages/DoctorsPage'
import CalendarPage from './pages/CalendarPage'
import DoctorSlotsPage from './pages/DoctorSlotsPage'
import CallLogsPage from './pages/CallLogsPage'
import RemindersPage from './pages/RemindersPage'
import AnalyticsPage from './pages/AnalyticsPage'
import UsersPage from './pages/UsersPage'
import ProfilePage from './pages/ProfilePage'
import TranscriptionDetailPage from './pages/TranscriptionDetailPage'
import { useAuth } from './contexts/AuthContext'

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = !!localStorage.getItem('access_token')
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

const RoleRoute = ({
  children,
  allow,
}: {
  children: React.ReactNode
  allow: ('ADMIN' | 'STAFF' | 'DOCTOR' | 'READONLY')[]
}) => {
  const { user } = useAuth()
  if (!localStorage.getItem('access_token')) return <Navigate to="/login" replace />
  // While user is loading from /auth/me, allow render; the page will guard itself
  if (user && !allow.includes(user.role)) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

const wrap = (title: string, page: React.ReactNode) => (
  <ProtectedRoute>
    <SimpleLayout title={title}>{page}</SimpleLayout>
  </ProtectedRoute>
)

function App() {
  const isAuthenticated = !!localStorage.getItem('access_token')

  return (
    <Routes>
      <Route path="/login" element={<StandaloneLoginPage />} />

      <Route path="/dashboard" element={
        <ProtectedRoute><SimpleDashboard /></ProtectedRoute>
      } />

      <Route path="/profile" element={wrap('My profile', <ProfilePage />)} />
      <Route path="/patients" element={wrap('Patients', <PatientsPage />)} />
      <Route path="/doctors" element={wrap('Doctors', <DoctorsPage />)} />
      <Route path="/calendar" element={wrap('Calendar', <CalendarPage />)} />

      <Route
        path="/slots"
        element={
          <RoleRoute allow={['ADMIN', 'DOCTOR', 'STAFF']}>
            <SimpleLayout title="Availability">
              <DoctorSlotsPage />
            </SimpleLayout>
          </RoleRoute>
        }
      />

      <Route path="/call-logs" element={wrap('Call Logs', <CallLogsPage />)} />
      <Route
        path="/transcriptions/:id"
        element={wrap('Transcription', <TranscriptionDetailPage />)}
      />
      <Route path="/reminders" element={wrap('Reminders', <RemindersPage />)} />
      <Route path="/analytics" element={wrap('Analytics', <AnalyticsPage />)} />

      <Route
        path="/users"
        element={
          <RoleRoute allow={['ADMIN']}>
            <SimpleLayout title="Users">
              <UsersPage />
            </SimpleLayout>
          </RoleRoute>
        }
      />

      <Route path="/" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
