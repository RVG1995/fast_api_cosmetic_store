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
import AdminProducts from './pages/admin/AdminProducts';
import AdminCategories from './pages/admin/AdminCategories';
import AdminSubcategories from './pages/admin/AdminSubcategories';
import AdminBrands from './pages/admin/AdminBrands';
import AdminCountries from './pages/admin/AdminCountries';
import HomePage from './pages/HomePage';

// Импорт стилей
import './styles/App.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            {/* Главная страница с продуктами */}
            <Route index element={<HomePage />} />
            
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
              path="admin/products" 
              element={
                <AdminRoute>
                  <AdminProducts />
                </AdminRoute>
              } 
            />
            {/* Новые маршруты для управления категориями, подкатегориями, брендами и странами */}
            <Route 
              path="admin/categories" 
              element={
                <AdminRoute>
                  <AdminCategories />
                </AdminRoute>
              } 
            />
            <Route 
              path="admin/subcategories" 
              element={
                <AdminRoute>
                  <AdminSubcategories />
                </AdminRoute>
              } 
            />
            <Route 
              path="admin/brands" 
              element={
                <AdminRoute>
                  <AdminBrands />
                </AdminRoute>
              } 
            />
            <Route 
              path="admin/countries" 
              element={
                <AdminRoute>
                  <AdminCountries />
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
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
