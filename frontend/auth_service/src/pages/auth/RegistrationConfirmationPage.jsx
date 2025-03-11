import React from 'react';
import { useLocation } from 'react-router-dom';

function RegistrationConfirmationPage() {
  const location = useLocation();
  const email = location.state?.email || 'указанный email';

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8 text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">
          Подтвердите вашу регистрацию
        </h1>
        <div className="text-gray-600">
          <p className="mb-4">
            На адрес <span className="font-semibold text-blue-600">{email}</span> было отправлено письмо с ссылкой для подтверждения регистрации.
          </p>
          <p className="mb-4">
            Пожалуйста, проверьте вашу почту и перейдите по ссылке в письме для активации аккаунта.
          </p>
          <p className="text-sm text-gray-500">
            Если вы не получили письмо, проверьте папку "Спам"
          </p>
        </div>
      </div>
    </div>
  );
}

export default RegistrationConfirmationPage;
