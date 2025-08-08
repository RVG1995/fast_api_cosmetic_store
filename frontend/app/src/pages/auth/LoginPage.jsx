// src/pages/auth/LoginPage.jsx

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // Состояние для хранения ошибок по каждому полю
  const [errors, setErrors] = useState({});
  const { login } = useAuth(); 

  // Проверяем URL на наличие параметра expired=true при загрузке компонента
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('expired') === 'true') {
      setErrors({ general: 'Ваша сессия истекла. Пожалуйста, войдите снова.' });
    }
  }, [location.search]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrors({});
    try {
      // Используем login из AuthContext вместо прямого вызова API
      const result = await login({
        username: email,
        password: password
      });
      
      if (result.success) {
        navigate('/user');
      } else {
        setErrors({ general: result.error || 'Ошибка входа' });
      }
    } catch (error) {
      console.error('Ошибка входа:', error);
      setErrors({ general: error.message || 'Произошла непредвиденная ошибка' });
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full max-w-md p-6 bg-white rounded shadow">
        <h2 className="text-2xl font-bold mb-6 text-center">Вход</h2>
        {/* Если есть общая ошибка */}
          {errors.general && (
            <p className="mb-4 text-red-500" role="alert">{errors.general}</p>
          )}
        <form onSubmit={handleLogin}>
          <div className="mb-4">
              <label htmlFor="login-email" className="block text-gray-700 mb-1">Электронная почта:</label>
            <input 
              type="email" 
              value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                required 
                id="login-email"
                name="email"
                autoComplete="email"
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? 'login-email-error' : undefined}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.email && (
                <p id="login-email-error" className="text-red-500 text-sm mt-1" role="alert">{errors.email}</p>
            )}
          </div>
          <div className="mb-4">
              <label htmlFor="login-password" className="block text-gray-700 mb-1">Пароль:</label>
            <input 
              type="password" 
              value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
                id="login-password"
                name="password"
                autoComplete="current-password"
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? 'login-password-error' : undefined}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.password && (
                <p id="login-password-error" className="text-red-500 text-sm mt-1" role="alert">{errors.password}</p>
            )}
          </div>
          <button type="submit" className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 transition duration-200">
            Войти
          </button>
        </form>
        <div className="mt-4 text-center">
          <a href="/forgot-password" className="text-blue-600 hover:underline">Забыли пароль?</a>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
