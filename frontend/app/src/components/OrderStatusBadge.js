import React from 'react';
import { Badge } from 'react-bootstrap';

/**
 * Компонент для отображения статуса заказа с соответствующим цветом
 * @param {Object} props - Свойства компонента
 * @param {Object} props.status - Объект статуса заказа, содержащий name и color
 * @returns {JSX.Element} - Badge компонент с соответствующим цветом и названием статуса
 */
const OrderStatusBadge = ({ status }) => {
  if (!status) return null;

  // Если указан цвет статуса, используем его
  if (status.color) {
    return (
      <Badge 
        style={{ backgroundColor: status.color, color: '#FFF' }}
        className="order-status-badge"
      >
        {status.name}
      </Badge>
    );
  }

  // Преобразуем код статуса в вариант бэджа Bootstrap
  const getVariant = (statusCode) => {
    const statusMap = {
      'NEW': 'info',
      'PROCESSING': 'primary',
      'SHIPPED': 'warning',
      'DELIVERED': 'success',
      'CANCELLED': 'danger',
      'RETURNED': 'secondary'
    };
    
    return statusMap[statusCode] || 'secondary';
  };

  return (
    <Badge 
      bg={getVariant(status.code)}
      className="order-status-badge"
    >
      {status.name}
    </Badge>
  );
};

export default OrderStatusBadge; 