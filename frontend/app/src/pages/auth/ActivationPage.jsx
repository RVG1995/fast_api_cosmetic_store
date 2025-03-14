// src/pages/auth/ActivationPage.jsx
import { useEffect, useCallback, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../utils/api';

function ActivationPage() {
  const navigate = useNavigate();
  const { token } = useParams();
  const [status, setStatus] = useState('loading');
  const { setUser } = useAuth();
  const [activationAttempted, setActivationAttempted] = useState(false);

  const activateAccount = useCallback(async () => {
    if (activationAttempted) return;
    setActivationAttempted(true);
    
    try {
      setStatus('loading');
      const response = await authAPI.activateUser(token);
      
      if (response.data && response.data.status === 'success') {
        setUser(response.data.user);
        setStatus('success');
        
        setTimeout(() => {
          navigate('/user');
        }, 1500);
      } else {
        setStatus('error');
      }
    } catch (error) {
      console.error('Ошибка активации:', error);
      setStatus('error');
    }
  }, [token, navigate, setUser, activationAttempted]);

  useEffect(() => {
    if (token) {
      activateAccount();
    }
  }, [token, activateAccount]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8 text-center">
        {status === 'loading' && (
          <div>
            <h2 className="text-xl font-semibold">Активация аккаунта...</h2>
            <div className="mt-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
            </div>
          </div>
        )}
        
        {status === 'success' && (
          <div>
            <h2 className="text-xl font-semibold text-green-600">
              Аккаунт успешно активирован!
            </h2>
            <p className="mt-4 text-gray-600">
              Вы будете перенаправлены в личный кабинет через несколько секунд...
            </p>
          </div>
        )}
        
        {status === 'error' && (
          <div>
            <h2 className="text-xl font-semibold text-red-600">
              Ошибка активации
            </h2>
            <p className="mt-4 text-gray-600">
              Ссылка для активации недействительна или устарела.
              Пожалуйста, попробуйте зарегистрироваться снова.
            </p>
            <button
              onClick={() => navigate('/register')}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Вернуться к регистрации
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ActivationPage;