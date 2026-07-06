import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { RegisterPage } from './pages/RegisterPage'
import { LoginPage } from './pages/LoginPage'
import { MembersPage } from './pages/MembersPage'
import { OrganizationPage } from './pages/OrganizationPage'
import { KeysPage } from './pages/KeysPage'
import { UploadPage } from './pages/UploadPage'
import { ResultsPage } from './pages/ResultsPage'
import { HistoryPage } from './pages/HistoryPage'
import { GlobalAdminsPage } from './pages/GlobalAdminsPage'
import { OrgRoute } from './components/OrgRoute'
import { AdminRoute } from './components/AdminRoute'
import { GlobalAdminRoute } from './components/GlobalAdminRoute'
import { Layout } from './components/Layout'
import { AuthProvider } from './auth/AuthProvider'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/organization"
              element={
                <AdminRoute>
                  <OrganizationPage />
                </AdminRoute>
              }
            />
            <Route
              path="/members"
              element={
                <AdminRoute>
                  <MembersPage />
                </AdminRoute>
              }
            />
            <Route
              path="/keys"
              element={
                <OrgRoute>
                  <KeysPage />
                </OrgRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <OrgRoute>
                  <UploadPage />
                </OrgRoute>
              }
            />
            <Route
              path="/results/:taskId"
              element={
                <OrgRoute>
                  <ResultsPage />
                </OrgRoute>
              }
            />
            <Route
              path="/history"
              element={
                <OrgRoute>
                  <HistoryPage />
                </OrgRoute>
              }
            />
            <Route
              path="/platform/global-admins"
              element={
                <GlobalAdminRoute>
                  <GlobalAdminsPage />
                </GlobalAdminRoute>
              }
            />
            <Route path="*" element={<HomePage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
