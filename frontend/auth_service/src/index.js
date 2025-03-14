//src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import reportWebVitals from './utils/reportWebVitals';
import './styles/output.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import 'bootstrap-icons/font/bootstrap-icons.css';

// Глобальный обработчик ошибок для отладки белого экрана
window.addEventListener('error', function(event) {
  console.error('Глобальная ошибка JS:', event.error);
});

// Обработчик непойманных промисов
window.addEventListener('unhandledrejection', function(event) {
  console.error('Необработанное отклонение промиса:', event.reason);
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
