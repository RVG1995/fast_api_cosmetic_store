// src/pages/auth/LoginPage.jsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../utils/api';

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // Состояние для хранения ошибок по каждому полю
  const [errors, setErrors] = useState({});
  const { setUser } = useAuth(); 

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrors({});
    try {
      const response = await authAPI.login({
        username: email,
        password: password
      });
      
      // Задержка для установки куки перед проверкой
      setTimeout(async () => {
        try {
          const userResponse = await authAPI.getCurrentUser();
          setUser(userResponse.data);
          navigate('/user');
        } catch (error) {
          console.error('Ошибка получения данных пользователя:', error);
          setErrors({ general: 'Не удалось получить данные пользователя' });
        }
      }, 500);
    } catch (error) {
      console.error('Ошибка входа:', error);
      
      // Обработка различных ошибок
      if (error.response?.status === 401) {
        setErrors({ general: 'Неверный email или пароль' });
      } else if (error.response?.status === 400) {
        setErrors({ general: error.response.data.detail || 'Ошибка при входе' });
      } else {
        setErrors({ general: 'Ошибка соединения с сервером' });
      }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full max-w-md p-6 bg-white rounded shadow">
        <h2 className="text-2xl font-bold mb-6 text-center">Вход</h2>
        {/* Если есть общая ошибка */}
        {errors.general && (
          <p className="mb-4 text-red-500">{errors.general}</p>
        )}
        <form onSubmit={handleLogin}>
          <div className="mb-4">
            <label className="block text-gray-700 mb-1">Электронная почта:</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.email && (
              <p className="text-red-500 text-sm mt-1">{errors.email}</p>
            )}
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 mb-1">Пароль:</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.password && (
              <p className="text-red-500 text-sm mt-1">{errors.password}</p>
            )}
          </div>
          <button type="submit" className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 transition duration-200">
            Войти
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
