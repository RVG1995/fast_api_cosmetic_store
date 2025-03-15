import React, { useEffect } from 'react';
import { Badge } from 'react-bootstrap';

/**
 * Компонент для отображения статуса заказа с соответствующим цветом Bootstrap
 * @param {Object} props - Свойства компонента
 * @param {Object} props.status - Объект статуса заказа, содержащий id и name
 * @returns {JSX.Element} - Badge компонент с соответствующим вариантом цвета Bootstrap
 */
const OrderStatusBadge = ({ status }) => {
  useEffect(() => {
    console.log('OrderStatusBadge - Получен статус:', status);
  }, [status]);

  if (!status) return null;

  // Сопоставление статусов со стандартными вариантами цветов Bootstrap
  const getStatusVariant = (status) => {
    // Карта соответствия по ID и именам статусов вариантам Bootstrap
    const statusVariantMap = {
      // По ID
      1: 'primary',   // Новый - синий
      2: 'warning',   // В обработке - желтый
      3: 'success',   // Оплачен - зеленый
      4: 'info',      // Отправлен - голубой
      5: 'success',   // Доставлен - тоже зеленый, но будет переопределен кастомным стилем
      6: 'danger',    // Отменен - красный
      
      // По названию (для страховки)
      'Новый': 'primary',
      'В обработке': 'warning',
      'Оплачен': 'success',
      'Отправлен': 'info',
      'Доставлен': 'success',
      'Отменен': 'danger'
    };
    
    // Проверяем сначала по ID, затем по имени
    if (status.id && statusVariantMap[status.id]) {
      return statusVariantMap[status.id];
    }
    
    if (status.name && statusVariantMap[status.name]) {
      return statusVariantMap[status.name];
    }
    
    // Если не нашли подходящий вариант, используем secondary по умолчанию
    return 'secondary';
  };

  // Определяем, является ли статус "Доставлен"
  const isDelivered = status.id === 5 || status.name === 'Доставлен';
  
  // Получаем вариант Bootstrap для статуса
  const statusVariant = getStatusVariant(status);
  
  return (
    <Badge 
      bg={statusVariant}
      style={isDelivered ? { backgroundColor: '#27ae60' } : undefined}
      className="order-status-badge"
    >
      {status.name}
    </Badge>
  );
};

export default OrderStatusBadge; 