import React, { useState } from 'react';
import { Container, Row, Col, Card, Tab, Nav } from 'react-bootstrap';
import ReviewList from '../../components/reviews/ReviewList';
import ReviewForm from '../../components/reviews/ReviewForm';
import { useAuth } from '../../context/AuthContext';

const ReviewsPage = () => {
  const { user } = useAuth();
  const [currentPage, setCurrentPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0); // Ключ для принудительной перезагрузки списка отзывов
  
  // Обработчик успешной отправки отзыва
  const handleReviewSubmitted = () => {
    // Перезагружаем список отзывов и переходим на первую страницу
    setCurrentPage(1);
    setReloadKey(prev => prev + 1);
  };
  
  // Обработчик изменения страницы
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  return (
    <Container className="py-4">
      <h1 className="mb-4">Отзывы о магазине</h1>
      
      <Row>
        <Col lg={4} className="mb-4">
          {/* Форма отзыва доступна только для авторизованных пользователей */}
          {user ? (
            <ReviewForm 
              onReviewSubmitted={handleReviewSubmitted} 
            />
          ) : (
            <Card className="shadow-sm mb-4">
              <Card.Header className="bg-primary text-white">
                <h5 className="mb-0">Оставить отзыв</h5>
              </Card.Header>
              <Card.Body>
                <p className="mb-0">
                  Для того чтобы оставить отзыв, необходимо <a href="/login">войти в систему</a>.
                </p>
              </Card.Body>
            </Card>
          )}
          
          <Card className="shadow-sm mb-4">
            <Card.Header>
              <h5 className="mb-0">О нашем магазине</h5>
            </Card.Header>
            <Card.Body>
              <p>
                Мы стремимся предоставлять лучшие товары и сервис. 
                Ваши отзывы помогают нам становиться лучше!
              </p>
              <ul className="mb-0">
                <li>Огромный выбор товаров</li>
                <li>Быстрая доставка</li>
                <li>Гарантия качества</li>
                <li>Отличное обслуживание</li>
              </ul>
            </Card.Body>
          </Card>
        </Col>
        
        <Col lg={8}>
          <Card className="shadow-sm mb-4">
            <Card.Header>
              <h5 className="mb-0">Отзывы наших клиентов</h5>
            </Card.Header>
            <Card.Body>
              {/* Ключ reloadKey используется для принудительной перезагрузки списка при добавлении нового отзыва */}
              <ReviewList 
                key={reloadKey}
                currentPage={currentPage}
                onPageChange={handlePageChange}
              />
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default ReviewsPage;