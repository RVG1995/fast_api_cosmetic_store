// src/App.js
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import RegistrationPage from './pages/auth/RegistrationPage';
import UserInfoPage from './pages/user/UserInfoPage';
import Layout from './components/layout/Layout';
import { AuthProvider } from "./context/AuthContext"; // Импортируем провайдер
import LoginPage from './pages/auth/LoginPage';
import RegistrationConfirmationPage from './pages/auth/RegistrationConfirmationPage';
import ActivationPage from './pages/auth/ActivationPage';
import PrivateRoute from './components/common/PrivateRoute';
import PublicOnlyRoute from './components/common/PublicOnlyRoute';
import AdminRoute from './components/common/AdminRoute';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminUsers from './pages/admin/AdminUsers';

// Импорт стилей
import './styles/App.css';

function App() {
  return (
    <AuthProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* Публичные маршруты только для неавторизованных пользователей */}
          <Route 
            path="register" 
            element={
              <PublicOnlyRoute>
                <RegistrationPage />
              </PublicOnlyRoute>
            } 
          />
          <Route 
            path="login" 
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            } 
          />
          <Route 
            path="registration-confirmation" 
            element={
              <PublicOnlyRoute>
                <RegistrationConfirmationPage />
              </PublicOnlyRoute>
            } 
          />
          <Route path="activate/:token" element={<ActivationPage />} />

          {/* Защищенные маршруты */}
          <Route 
            path="user" 
            element={
              <PrivateRoute>
                <UserInfoPage />
              </PrivateRoute>
            } 
          />

          {/* Административные маршруты */}
          <Route 
            path="admin" 
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            } 
          />
          <Route 
            path="admin/users" 
            element={
              <AdminRoute>
                <AdminUsers />
              </AdminRoute>
            } 
          />
          <Route 
            path="admin/permissions" 
            element={
              <AdminRoute requireSuperAdmin={true}>
                {/* Здесь будет компонент для управления правами */}
                <div className="container py-5">
                  <h2>Управление правами (только для суперадмина)</h2>
                </div>
              </AdminRoute>
            } 
          />
        </Route>
      </Routes>
    </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
