import React from 'react';

const LoginModal = ({ onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full">
      <h2 className="text-xl font-bold mb-4">Вход в аккаунт</h2>
      <p className="mb-4">Чтобы добавить в избранное, войдите или зарегистрируйтесь.</p>
      <div className="flex justify-end gap-2">
        <a href="/login" className="btn btn-primary">Войти</a>
        <button className="btn btn-secondary" onClick={onClose}>Закрыть</button>
      </div>
    </div>
  </div>
);

export default LoginModal; 