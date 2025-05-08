import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Card, Alert, Button, Spinner } from 'react-bootstrap';
import axios from 'axios';
import { API_URLS } from '../utils/constants';

const UnsubscribePage = () => {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();
  const email = searchParams.get('email');
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  // Отправляем запрос на отписку при загрузке страницы (если есть email и orderId)
  useEffect(() => {
    const unsubscribe = async () => {
      if (!orderId || !email) {
        setError('Не указан ID заказа или email');
        return;
      }
      
      setLoading(true);
      
      try {
        const response = await axios.post(
          `${API_URLS.ORDER_SERVICE}/orders/${orderId}/unsubscribe`,
          { email }
        );
        
        if (response.data.success) {
          setSuccess(true);
        } else {
          setError(response.data.message || 'Не удалось отписаться от уведомлений');
        }
      } catch (err) {
        console.error('Ошибка при отписке от уведомлений', err);
        setError(err.response?.data?.detail || 'Произошла ошибка при отписке от уведомлений');
      } finally {
        setLoading(false);
      }
    };
    
    unsubscribe();
  }, [orderId, email]);
  
  return (
    <div className="unsubscribe-container" style={{ maxWidth: '600px', margin: '0 auto', padding: '20px' }}>
      <Card>
        <Card.Header as="h4" className="text-center">Отписка от уведомлений</Card.Header>
        <Card.Body className="text-center">
          {loading ? (
            <div className="text-center my-4">
              <Spinner animation="border" variant="primary" />
              <p className="mt-3">Выполняется отписка от уведомлений...</p>
            </div>
          ) : error ? (
            <Alert variant="danger">
              <Alert.Heading>Ошибка</Alert.Heading>
              <p>{error}</p>
              <div className="d-flex justify-content-center mt-3">
                <Button variant="primary" onClick={() => navigate('/')}>
                  Вернуться на главную
                </Button>
              </div>
            </Alert>
          ) : success ? (
            <div>
              <div className="success-icon mb-3">✓</div>
              <h3>Вы успешно отписались от уведомлений</h3>
              <p className="mb-4">Вы больше не будете получать уведомления о статусе заказа №{orderId}.</p>
              <Button variant="primary" onClick={() => navigate('/')}>
                Вернуться на главную
              </Button>
            </div>
          ) : null}
        </Card.Body>
      </Card>
    </div>
  );
};

export default UnsubscribePage; 