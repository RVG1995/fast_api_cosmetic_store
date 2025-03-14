// src/App.js
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import RegistrationPage from './pages/auth/RegistrationPage';
import UserInfoPage from './pages/user/UserInfoPage';
import Layout from './components/layout/Layout';
import { AuthProvider } from "./context/AuthContext"; // Импортируем провайдер
import { CategoryProvider } from "./context/CategoryContext"; // Импортируем провайдер категорий
import LoginPage from './pages/auth/LoginPage';
import RegistrationConfirmationPage from './pages/auth/RegistrationConfirmationPage';
import ActivationPage from './pages/auth/ActivationPage';
import PrivateRoute from './components/common/PrivateRoute';
import PublicOnlyRoute from './components/common/PublicOnlyRoute';
import AdminRoute from './components/common/AdminRoute';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminUsers from './pages/admin/AdminUsers';
import AdminProducts from './pages/admin/AdminProducts';
import AdminProductDetail from './pages/admin/AdminProductDetail';
import AdminCategories from './pages/admin/AdminCategories';
import AdminSubcategories from './pages/admin/AdminSubcategories';
import AdminBrands from './pages/admin/AdminBrands';
import AdminCountries from './pages/admin/AdminCountries';
import AdminCarts from './pages/admin/AdminCarts'; // Импортируем новую страницу корзин
import AdminCartDetail from './pages/admin/AdminCartDetail'; // Импортируем страницу с деталями корзины
import HomePage from './pages/HomePage';
import ProductsPage from './pages/ProductsPage';
import ProductDetailPage from './pages/ProductDetailPage';
import CartPage from './pages/CartPage'; // Импортируем страницу корзины

// Импорт стилей
import './styles/App.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CategoryProvider>
          <Routes>
            <Route path="/" element={<Layout />}>
              {/* Главная страница с продуктами */}
              <Route index element={<HomePage />} />
              
              {/* Страница с фильтрацией товаров */}
              <Route path="products" element={<ProductsPage />} />
              
              {/* Страница детальной информации о товаре */}
              <Route path="products/:productId" element={<ProductDetailPage />} />
              
              {/* Страница корзины */}
              <Route path="cart" element={<CartPage />} />
              
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
              <Route 
                path="admin/products/:productId" 
                element={
                  <AdminRoute>
                    <AdminProductDetail />
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
              {/* Новые маршруты для управления корзинами пользователей */}
              <Route 
                path="admin/carts" 
                element={
                  <AdminRoute>
                    <AdminCarts />
                  </AdminRoute>
                } 
              />
              <Route 
                path="admin/carts/:cartId" 
                element={
                  <AdminRoute>
                    <AdminCartDetail />
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
        </CategoryProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
