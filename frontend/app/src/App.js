// src/App.js
import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import RegistrationPage from './pages/auth/RegistrationPage';
import UserInfoPage from './pages/user/UserInfoPage';
import ChangePasswordPage from './pages/user/ChangePasswordPage'; // Импортируем страницу смены пароля
import Layout from './components/layout/Layout';
import { AuthProvider } from "./context/AuthContext"; // Импортируем провайдер
import { CategoryProvider } from "./context/CategoryContext"; // Импортируем провайдер категорий
import { OrderProvider } from "./context/OrderContext"; // Импортируем провайдер заказов
import LoginPage from './pages/auth/LoginPage';
import RegistrationConfirmationPage from './pages/auth/RegistrationConfirmationPage';
import ActivationPage from './pages/auth/ActivationPage';
import PrivateRoute from './components/common/PrivateRoute';
import PublicOnlyRoute from './components/common/PublicOnlyRoute';
import AdminRoute from './components/common/AdminRoute';
import HomePage from './pages/HomePage';
import ProductsPage from './pages/ProductsPage'; // Импортируем настоящую страницу ProductsPage
import ProductDetailPage from './pages/ProductDetailPage';
import CartPage from './pages/CartPage'; // Импортируем страницу корзины
import CheckoutPage from './pages/CheckoutPage'; // Импортируем страницу оформления заказа
import OrdersPage from './pages/user/OrdersPage'; // Импортируем страницу заказов пользователя
import OrderDetailPage from './pages/user/OrderDetailPage'; // Импортируем страницу деталей заказа
import ReviewsPage from './pages/reviews/ReviewsPage'; // Импортируем страницу отзывов
import ReviewPage from './pages/reviews/ReviewPage'; // Импортируем страницу детального просмотра отзыва
import ScrollToTop from './components/layout/ScrollToTop';
// Импорт стилей перемещен в начало файла
import './styles/App.css';

// Ленивая загрузка админских компонентов
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const AdminUsers = lazy(() => import('./pages/admin/AdminUsers'));
const AdminProducts = lazy(() => import('./pages/admin/AdminProducts'));
const AdminProductDetail = lazy(() => import('./pages/admin/AdminProductDetail'));
const AdminCategories = lazy(() => import('./pages/admin/AdminCategories'));
const AdminSubcategories = lazy(() => import('./pages/admin/AdminSubcategories'));
const AdminBrands = lazy(() => import('./pages/admin/AdminBrands'));
const AdminCountries = lazy(() => import('./pages/admin/AdminCountries'));
const AdminCarts = lazy(() => import('./pages/admin/AdminCarts'));
const AdminCartDetail = lazy(() => import('./pages/admin/AdminCartDetail'));
const AdminOrders = lazy(() => import('./pages/admin/AdminOrders'));
const AdminOrderDetail = lazy(() => import('./pages/admin/AdminOrderDetail'));
const AdminOrderStatuses = lazy(() => import('./pages/admin/AdminOrderStatuses'));
const AdminPaymentStatuses = lazy(() => import('./pages/admin/AdminPaymentStatuses'));
const AdminReviewsPage = lazy(() => import('./pages/admin/reviews/AdminReviewsPage'));
const AdminReviewDetailPage = lazy(() => import('./pages/admin/reviews/AdminReviewDetailPage'));

// Удаляем временную замену ProductsPage
// const ProductsPage = HomePage;

// Компонент загрузки для Suspense
const Loading = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    padding: '2rem',
    flexDirection: 'column',
    minHeight: '200px'
  }}>
    <div className="spinner-border text-primary" role="status" style={{ width: '3rem', height: '3rem' }}>
      <span className="visually-hidden">Загрузка...</span>
    </div>
    <p className="mt-3">Загружаем страницу...</p>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <AuthProvider>
        <CategoryProvider>
          <OrderProvider>
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
                
                {/* Страница оформления заказа */}
                <Route path="checkout" element={<CheckoutPage />} />
                
                {/* Страницы заказов пользователя */}
                <Route path="orders" element={
                  <PrivateRoute>
                    <OrdersPage />
                  </PrivateRoute>
                } />
                
                <Route path="orders/:orderId" element={
                  <PrivateRoute>
                    <OrderDetailPage />
                  </PrivateRoute>
                } />
                
                {/* Маршруты для отзывов */}
                <Route path="reviews" element={<ReviewsPage />} />
                <Route path="reviews/:id" element={<ReviewPage />} />
                
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

                {/* Защищенные маршруты - используем обычные импорты, убрали Suspense */}
                <Route 
                  path="user" 
                  element={
                    <PrivateRoute>
                      <UserInfoPage />
                    </PrivateRoute>
                  } 
                />
                <Route 
                  path="user/change-password" 
                  element={
                    <PrivateRoute>
                      <ChangePasswordPage />
                    </PrivateRoute>
                  } 
                />

                {/* Административные маршруты с ленивой загрузкой */}
                <Route 
                  path="admin" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminDashboard />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/users" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminUsers />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/products" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminProducts />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/products/:productId" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminProductDetail />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                {/* Новые маршруты для управления категориями, подкатегориями, брендами и странами */}
                <Route 
                  path="admin/categories" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminCategories />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/subcategories" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminSubcategories />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/brands" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminBrands />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/countries" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminCountries />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                {/* Новые маршруты для управления корзинами пользователей */}
                <Route 
                  path="admin/carts" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminCarts />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/carts/:cartId" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminCartDetail />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                {/* Новые маршруты для управления заказами */}
                <Route 
                  path="admin/orders" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminOrders />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/orders/:orderId" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminOrderDetail />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/order-statuses" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminOrderStatuses />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/payment-statuses" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminPaymentStatuses />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                {/* Маршруты для управления отзывами */}
                <Route 
                  path="admin/reviews" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminReviewsPage />
                      </Suspense>
                    </AdminRoute>
                  } 
                />
                <Route 
                  path="admin/reviews/:reviewId" 
                  element={
                    <AdminRoute>
                      <Suspense fallback={<Loading />}>
                        <AdminReviewDetailPage />
                      </Suspense>
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
          </OrderProvider>
        </CategoryProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
