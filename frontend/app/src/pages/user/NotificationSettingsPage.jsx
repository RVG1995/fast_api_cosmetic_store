import React, { useEffect, useState } from 'react';
import { useNotifications } from '../../context/NotificationContext';
import { useAuth } from '../../context/AuthContext';
import { Link } from 'react-router-dom';
// ... при необходимости импорт стилей или компонентов UI ...

const NotificationSettingsPage = () => {
  const { user } = useAuth();
  const { settings, loading, error, fetchSettings, createSetting, updateSetting } = useNotifications();
  const [settingsMap, setSettingsMap] = useState({});
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (user && !initialized) {
      fetchSettings();
      setInitialized(true);
    }
  }, [user, initialized]);

  useEffect(() => {
    if (settings && settings.length > 0) {
      const map = settings.reduce((acc, item) => {
        acc[item.event_type] = item;
        return acc;
      }, {});
      setSettingsMap(map);
    }
  }, [settings]);

  const handleToggle = (eventType, field) => {
    const setting = settingsMap[eventType];
    if (setting) {
      const payload = { [field]: !setting[field] };
      updateSetting(eventType, payload);
    } else {
      const payload = {
        event_type: eventType,
        email_enabled: field === 'email_enabled',
        push_enabled: field === 'push_enabled'
      };
      createSetting(eventType, payload);
    }
  };

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
                {settings.map(setting => (
                  <tr key={setting.event_type}>
                    <td>{setting.event_type_label || setting.event_type}</td>
                    <td className="text-center">
                      <div className="form-check form-switch d-flex justify-content-center">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`email_${setting.event_type}`}
                          checked={!!setting.email_enabled}
                          onChange={() => handleToggle(setting.event_type, 'email_enabled')}
                        />
                      </div>
                    </td>
                    <td className="text-center">
                      <div className="form-check form-switch d-flex justify-content-center">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`push_${setting.event_type}`}
                          checked={!!setting.push_enabled}
                          onChange={() => handleToggle(setting.event_type, 'push_enabled')}
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