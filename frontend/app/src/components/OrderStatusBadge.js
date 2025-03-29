import React, { useMemo, memo } from 'react';
import { Badge } from 'react-bootstrap';

/**
 * Компонент для отображения статуса заказа с соответствующим цветом Bootstrap
 * @param {Object} props - Свойства компонента
 * @param {Object} props.status - Объект статуса заказа, содержащий id и name
 * @param {string} props.className - Дополнительные CSS классы
 * @returns {JSX.Element} - Badge компонент с соответствующим вариантом цвета Bootstrap
 */
const OrderStatusBadge = ({ status, className = '' }) => {
  // Карта соответствия статусов вариантам Bootstrap
  const statusVariantMap = useMemo(() => ({
    // По ID
    1: 'primary',   // Новый - синий
    2: 'warning',   // В обработке - желтый
    3: 'success',   // Оплачен - зеленый
    4: 'info',      // Отправлен - голубой
    5: 'success',   // Доставлен - зеленый (с кастомным стилем)
    6: 'danger',    // Отменен - красный
    
    // По названию (для страховки)
    'Новый': 'primary',
    'В обработке': 'warning',
    'Оплачен': 'success',
    'Отправлен': 'info',
    'Доставлен': 'success',
    'Отменен': 'danger'
  }), []);

  // Мемоизированные вычисления для варианта и стиля
  const { statusVariant, customStyle } = useMemo(() => {
    if (!status) {
      return { statusVariant: 'secondary', customStyle: undefined };
    }
    
    // Проверяем сначала по ID, затем по имени
    let variant;
    if (status.id && statusVariantMap[status.id]) {
      variant = statusVariantMap[status.id];
    } else if (status.name && statusVariantMap[status.name]) {
      variant = statusVariantMap[status.name];
    } else {
      variant = 'secondary'; // По умолчанию серый
    }
    
    // Определяем, является ли статус "Доставлен"
    const isDelivered = status.id === 5 || status.name === 'Доставлен';
    
    // Применяем кастомный стиль только для статуса "Доставлен"
    const style = isDelivered ? { backgroundColor: '#27ae60' } : undefined;
    
    return { statusVariant: variant, customStyle: style };
  }, [status, statusVariantMap]);

  // Если статус отсутствует, не рендерим компонент
  if (!status) return null;
  
  return (
    <Badge 
      bg={statusVariant}
      style={customStyle}
      className={`order-status-badge ${className}`}
    >
      {status.name}
    </Badge>
  );
};

export default memo(OrderStatusBadge); 