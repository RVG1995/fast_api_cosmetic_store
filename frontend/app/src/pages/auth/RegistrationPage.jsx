// src/RefistrationPage.jsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../../utils/api';

function RegistrationPage() {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [personalDataAgreement, setPersonalDataAgreement] = useState(false);
  const [notificationAgreement, setNotificationAgreement] = useState(false);
  // Состояние для хранения ошибок по каждому полю
  const [errors, setErrors] = useState({});

  const handleRegistration = async (e) => {
    e.preventDefault();
    setErrors({});

    // Проверка валидности данных
    let formErrors = {};
    
    if (!personalDataAgreement) {
      formErrors.personalDataAgreement = 'Необходимо согласие на обработку персональных данных';
    }
    
    if (Object.keys(formErrors).length > 0) {
      setErrors(formErrors);
      return;
    }
    
    try {
      const response = await authAPI.register({
        first_name: firstName,
        last_name: lastName,
        email,
        password,
        confirm_password: confirmPassword,
        personal_data_agreement: personalDataAgreement,
        notification_agreement: notificationAgreement
      });
      
      console.log('Регистрация успешна:', response.data);
      navigate('/registration-confirmation', { state: { email } });
    } catch (error) {
      console.error('Ошибка регистрации:', error);
      
      if (error.response?.data?.detail) {
        // Серверная ошибка с деталями
        if (typeof error.response.data.detail === 'string') {
          setErrors({ general: error.response.data.detail });
        } else if (Array.isArray(error.response.data.detail)) {
          // Ошибки валидации в массиве
          const validationErrors = error.response.data.detail || [];
          
          validationErrors.forEach(err => {
            const field = err.loc && err.loc.length > 1 ? err.loc[1] : 'general'; // Поле, в котором ошибка
            formErrors[field] = err.msg || JSON.stringify(err);
          });
          
          setErrors(formErrors);
        } else {
          // Если detail - это объект, а не строка или массив
          setErrors({ general: JSON.stringify(error.response.data.detail) });
        }
      } else if (error.response?.status === 422) {
        // Ошибки валидации
        const validationErrors = error.response.data?.detail || [];
        
        if (Array.isArray(validationErrors)) {
          validationErrors.forEach(err => {
            const field = err.loc && err.loc.length > 1 ? err.loc[1] : 'general'; // Поле, в котором ошибка
            formErrors[field] = err.msg || JSON.stringify(err);
          });
        } else {
          formErrors.general = 'Ошибка валидации данных';
        }
        
        setErrors(formErrors);
      } else {
        setErrors({ general: 'Ошибка при регистрации. Пожалуйста, попробуйте позже.' });
      }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full max-w-md p-6 bg-white rounded shadow">
        <h2 className="text-2xl font-bold mb-6 text-center">Регистрация</h2>
        {/* Если есть общая ошибка */}
        {errors.general && (
          <p className="mb-4 text-red-500">{errors.general}</p>
        )}
        <form onSubmit={handleRegistration}>
          <div className="mb-4">
            <label className="block text-gray-700 mb-1">Имя пользователя:</label>
            <input 
              type="text" 
              value={firstName} 
              onChange={(e) => setFirstName(e.target.value)} 
              required 
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.first_name && (
              <p className="text-red-500 text-sm mt-1">{errors.first_name}</p>
            )}
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 mb-1">Фамилия пользователя:</label>
            <input 
              type="text" 
              value={lastName} 
              onChange={(e) => setLastName(e.target.value)} 
              required 
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.last_name && (
              <p className="text-red-500 text-sm mt-1">{errors.last_name}</p>
            )}
          </div>
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
          <div className="mb-4">
            <label className="block text-gray-700 mb-1">Подтвердите пароль:</label>
            <input 
              type="password" 
              value={confirmPassword} 
              onChange={(e) => setConfirmPassword(e.target.value)} 
              required 
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
            />
            {errors.confirm_password && (
              <p className="text-red-500 text-sm mt-1">{errors.confirm_password}</p>
            )}
          </div>
          
          {/* Согласие на обработку персональных данных */}
          <div className="mb-4">
            <div className="flex items-center">
              <input 
                type="checkbox" 
                id="personalDataAgreement"
                checked={personalDataAgreement} 
                onChange={(e) => setPersonalDataAgreement(e.target.checked)} 
                required
                className="mr-2"
              />
              <label htmlFor="personalDataAgreement" className="text-gray-700">
                Я согласен на обработку персональных данных
              </label>
            </div>
            {errors.personalDataAgreement && (
              <p className="text-red-500 text-sm mt-1">{errors.personalDataAgreement}</p>
            )}
          </div>
          
          {/* Согласие на получение уведомлений */}
          <div className="mb-6">
            <div className="flex items-center">
              <input 
                type="checkbox" 
                id="notificationAgreement"
                checked={notificationAgreement} 
                onChange={(e) => setNotificationAgreement(e.target.checked)} 
                className="mr-2"
              />
              <label htmlFor="notificationAgreement" className="text-gray-700">
                Я хочу получать уведомления о новинках и акциях
              </label>
            </div>
          </div>
          
          <button type="submit" className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 transition duration-200">
            Зарегистрироваться
          </button>
        </form>
      </div>
    </div>
  );
}

export default RegistrationPage;
