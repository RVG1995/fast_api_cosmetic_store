import React, { useEffect, useState } from 'react';
import { useNotifications } from '../../context/NotificationContext';
import { useAuth } from '../../context/AuthContext';
import { Link } from 'react-router-dom';
// ... при необходимости импорт стилей или компонентов UI ...

// Предопределённые типы уведомлений в системе
const AVAILABLE_EVENT_TYPES = [
  { id: 'review.created', name: 'Новый отзыв на товар', adminOnly: true },
  { id: 'review.reply', name: 'Ответ на ваш отзыв', adminOnly: false },
  { id: 'service.critical_error', name: 'Критические ошибки в сервисе', adminOnly: true },
  { id: 'order.created', name: 'Создание заказа', adminOnly: false },
  { id: 'order.status_changed', name: 'Изменение статуса заказа', adminOnly: false },
  { id: 'product.low_stock', name: 'Низкое количество товара на складе', adminOnly: true }
];

const NotificationSettingsPage = () => {
  const { user } = useAuth();
  const { settings, loading, error, fetchSettings, createSetting, updateSetting } = useNotifications();
  const [settingsMap, setSettingsMap] = useState({});
  // Используем useRef для отслеживания первого запроса
  const [initialized, setInitialized] = useState(false);

  // Фильтруем типы событий в зависимости от роли пользователя
  const filteredEventTypes = AVAILABLE_EVENT_TYPES.filter(eventType => 
    !eventType.adminOnly || (user && (user.is_admin || user.is_super_admin))
  );

  useEffect(() => {
    // Загружаем настройки только раз при монтировании компонента
    if (user && !initialized) {
      fetchSettings();
      setInitialized(true);
    }
  }, [user, initialized]);

  // Преобразуем массив настроек в объект для удобного доступа по event_type
  useEffect(() => {
    if (settings && settings.length > 0) {
      const map = settings.reduce((acc, item) => {
        acc[item.event_type] = item;
        return acc;
      }, {});
      setSettingsMap(map);
    }
  }, [settings]);

  // Обработчик для создания/обновления настройки
  const handleToggle = (eventType, field) => {
    const setting = settingsMap[eventType];
    
    if (setting) {
      // Обновляем существующую настройку
      const payload = { [field]: !setting[field] };
      updateSetting(eventType, payload);
    } else {
      // Создаем новую настройку
      const payload = {
        event_type: eventType,
        email_enabled: field === 'email_enabled',
        push_enabled: field === 'push_enabled'
      };
      createSetting(eventType, payload);
    }
  };

  // Проверяем, включена ли опция для типа события
  const isEnabled = (eventType, field) => {
    return settingsMap[eventType] ? settingsMap[eventType][field] : false;
  };

  if (loading) return <div className="text-center py-5">Загрузка...</div>;

  return (
    <div className="container py-5">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1 className="mb-0">Настройки уведомлений</h1>
        <Link to="/user" className="btn btn-outline-primary">
          <i className="bi bi-arrow-left me-2"></i>Вернуться к профилю
        </Link>
      </div>

      <div className="card shadow">
        <div className="card-header bg-primary text-white">
          <h2 className="fs-4 mb-0">Управление уведомлениями</h2>
        </div>
        
        <div className="card-body">
          {error && <div className="alert alert-danger mb-4">{error.message || 'Ошибка при загрузке настроек'}</div>}
          
          <p className="text-muted mb-4">Выберите типы уведомлений, которые хотите получать, и способы их доставки.</p>
          
          <div className="alert alert-info mb-4">
            <i className="bi bi-info-circle-fill me-2"></i>
            <strong>Примечание:</strong> В текущей версии системы:
            <ul className="mb-0 mt-2">
              <li>Push-уведомления временно недоступны (требуется мобильное приложение)</li>
              <li>Email-уведомления о заказах отправляются независимо от этих настроек</li>
              <li>Интеграция между сервисами в разработке</li>
            </ul>
          </div>
          
          <div className="table-responsive">
            <table className="table table-hover">
              <thead className="table-light">
                <tr>
                  <th style={{width: '50%'}}>Тип уведомления</th>
                  <th className="text-center">Email</th>
                  <th className="text-center">Push</th>
                </tr>
              </thead>
              <tbody>
                {filteredEventTypes.map(eventType => (
                  <tr key={eventType.id}>
                    <td>{eventType.name}</td>
                    <td className="text-center">
                      <div className="form-check form-switch d-flex justify-content-center">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`email_${eventType.id}`}
                          checked={isEnabled(eventType.id, 'email_enabled')}
                          onChange={() => handleToggle(eventType.id, 'email_enabled')}
                        />
                      </div>
                    </td>
                    <td className="text-center">
                      <div className="form-check form-switch d-flex justify-content-center">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`push_${eventType.id}`}
                          checked={isEnabled(eventType.id, 'push_enabled')}
                          onChange={() => handleToggle(eventType.id, 'push_enabled')}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationSettingsPage; 