import React, { useEffect, useState } from 'react';
import { Card, Row, Col, ProgressBar, Spinner, Alert } from 'react-bootstrap';
import { reviewAPI } from '../../utils/api';

const ReviewStats = ({ productId = null }) => {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      setIsLoading(true);
      setError(null);

      try {
        let response;
        
        // Получаем статистику в зависимости от типа (товар или магазин)
        if (productId) {
          response = await reviewAPI.getProductStats(productId);
        } else {
          response = await reviewAPI.getStoreStats();
        }
        
        setStats(response.data);
      } catch (error) {
        console.error('Ошибка при загрузке статистики:', error);
        setError('Не удалось загрузить статистику отзывов');
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, [productId]);

  // Вычисляем процент для каждого рейтинга
  const calculatePercentage = (count, total) => {
    if (!total) return 0;
    return Math.round((count / total) * 100);
  };

  // Отображаем звезды для среднего рейтинга
  const renderStars = (rating) => {
    // Защита от undefined
    if (rating === undefined) return null;
    
    const roundedRating = Math.round(rating * 2) / 2; // Округляем до ближайшего 0.5
    
    return (
      <div className="d-flex align-items-center">
        {[1, 2, 3, 4, 5].map((i) => {
          // Определяем заполнение звезды (полная, половина или пустая)
          let starClass = i <= Math.floor(roundedRating) 
            ? 'bi bi-star-fill text-warning' 
            : 'bi bi-star text-muted';
          
          return (
            <i 
              key={i} 
              className={starClass}
              style={{ fontSize: '1.25rem', margin: '0 2px' }}
            />
          );
        })}
        
        <span className="ms-2 fw-bold">{rating.toFixed(1)}</span>
      </div>
    );
  };

  if (isLoading) {
    return (
      <Card className="shadow-sm mb-4">
        <Card.Body className="text-center py-4">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2">Загрузка статистики отзывов...</p>
        </Card.Body>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="danger" className="mb-4">
        {error}
      </Alert>
    );
  }

  if (!stats || !stats.total_reviews || stats.average_rating === undefined) {
    // Не отображаем ничего, так как отсутствие отзывов уже показано в компоненте ReviewList
    return null;
  }

  return (
    <Card className="shadow-sm mb-4">
      <Card.Header className="bg-light">
        <h5 className="mb-0">
          <i className="bi bi-bar-chart-fill me-2"></i>
          {productId ? 'Рейтинг товара' : 'Рейтинг магазина'}
        </h5>
      </Card.Header>
      <Card.Body>
        <Row>
          <Col md={4} className="text-center mb-3 mb-md-0">
            <div className="display-4 fw-bold text-primary mb-0">
              {stats.average_rating.toFixed(1)}
            </div>
            <div className="mb-2">
              {renderStars(stats.average_rating)}
            </div>
            <div className="text-muted">
              <i className="bi bi-chat-text me-1"></i>
              {stats.total_reviews} {stats.total_reviews === 1 ? 'отзыв' : 
                stats.total_reviews < 5 ? 'отзыва' : 'отзывов'}
            </div>
          </Col>
          
          <Col md={8}>
            <div className="ratings-breakdown">
              {[5, 4, 3, 2, 1].map((rating) => {
                const count = stats.rating_counts[rating] || 0;
                const percentage = calculatePercentage(count, stats.total_reviews);
                
                return (
                  <div key={rating} className="d-flex align-items-center mb-2">
                    <div className="me-2" style={{ width: '60px' }}>
                      <span>{rating}</span>
                      <i 
                        className="bi bi-star-fill text-warning ms-1"
                      />
                    </div>
                    
                    <ProgressBar 
                      now={percentage} 
                      className="flex-grow-1" 
                      style={{ height: '10px' }}
                      variant={
                        rating >= 4 ? 'success' : 
                        rating === 3 ? 'info' : 
                        rating === 2 ? 'warning' : 'danger'
                      }
                    />
                    
                    <div className="ms-2" style={{ width: '45px' }}>
                      {percentage}%
                    </div>
                  </div>
                );
              })}
            </div>
          </Col>
        </Row>
      </Card.Body>
    </Card>
  );
};

export default ReviewStats; 