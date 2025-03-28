import React, { useState, useEffect } from 'react';
import { Card, Alert, Spinner, Container, Row, Col, Button } from 'react-bootstrap';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { reviewAPI } from '../../utils/api';
import { formatDate } from '../../utils/helpers';
import AdminCommentSection from './AdminCommentSection';
import AdminReviewActions from './AdminReviewActions';
import { useAuth } from '../../context/AuthContext';

const ReviewDetail = () => {
  const { reviewId } = useParams();
  const [review, setReview] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const { isAdmin, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchReview = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Получаем детали отзыва в зависимости от роли пользователя
        let response;
        
        if (user && isAdmin) {
          response = await reviewAPI.admin.getReview(reviewId);
        } else {
          response = await reviewAPI.getReview(reviewId);
        }
        
        setReview(response.data);
      } catch (error) {
        console.error('Ошибка при загрузке отзыва:', error);
        
        if (error.response?.status === 404) {
          setError('Отзыв не найден');
        } else if (error.response?.status === 403) {
          setError('У вас нет доступа к этому отзыву');
        } else {
          setError('Не удалось загрузить отзыв. Пожалуйста, попробуйте позже.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    if (reviewId) {
      fetchReview();
    }
  }, [reviewId, isAdmin, user]);

  // Обработка реакции (лайк/дизлайк)
  const handleReaction = async (reactionType) => {
    if (isProcessing || !user) return;
    
    setIsProcessing(true);
    try {
      const currentReaction = review.user_reaction;
      let updatedReview;
      
      if (currentReaction === reactionType) {
        // Если уже стоит такая реакция - удаляем её
        updatedReview = await reviewAPI.deleteReaction(review.id);
      } else {
        // Иначе добавляем или обновляем реакцию
        updatedReview = await reviewAPI.addReaction(review.id, reactionType);
      }
      
      setReview(updatedReview);
    } catch (error) {
      console.error('Ошибка при обработке реакции:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Форматирование для отображения звезд рейтинга
  const renderStars = (rating) => {
    const stars = [];
    for (let i = 0; i < 5; i++) {
      stars.push(
        <i 
          key={i} 
          className={i < rating ? 'bi bi-star-fill text-warning' : 'bi bi-star text-muted'}
          style={{ fontSize: '1.25rem' }}
        />
      );
    }
    return stars;
  };

  const handleBackClick = () => {
    navigate(-1); // Возврат на предыдущую страницу
  };

  if (isLoading) {
    return (
      <Container className="my-4">
        <div className="text-center py-5">
          <Spinner animation="border" variant="primary" />
          <p className="mt-3">Загрузка отзыва...</p>
        </div>
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="my-4">
        <Alert variant="danger">
          {error}
        </Alert>
        <Button 
          variant="outline-primary" 
          onClick={handleBackClick}
          className="mt-3"
        >
          <i className="bi bi-chevron-left me-2"></i>
          Вернуться назад
        </Button>
      </Container>
    );
  }

  if (!review) {
    return (
      <Container className="my-4">
        <Alert variant="warning">
          Отзыв не найден
        </Alert>
        <Button 
          variant="outline-primary" 
          onClick={handleBackClick}
          className="mt-3"
        >
          <i className="bi bi-chevron-left me-2"></i>
          Вернуться назад
        </Button>
      </Container>
    );
  }

  return (
    <Container className="my-4">
      <Button 
        variant="outline-primary" 
        onClick={handleBackClick}
        className="mb-3"
      >
        <i className="bi bi-chevron-left me-2"></i>
        Вернуться назад
      </Button>
      
      <Card className="shadow-sm">
        <Card.Header className="bg-light">
          <h4 className="mb-0">Детали отзыва</h4>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={8}>
              <div className="d-flex align-items-center mb-2">
                {renderStars(review.rating)}
                <span className="ms-2 fw-bold">{review.rating}/5</span>
              </div>
              
              {review.product_name && (
                <h5 className="mb-3">
                  <Link to={`/product/${review.product_id}`} className="text-decoration-none">
                    {review.product_name}
                  </Link>
                </h5>
              )}
              
              <p className="lead">{review.content || <em className="text-muted">Отзыв без текста</em>}</p>
            </Col>
            
            <Col md={4}>
              <div className="text-md-end">
                <div className="text-muted mb-2">
                  <i className="bi bi-calendar me-1"></i>
                  {formatDate(review.created_at)}
                </div>
                
                <div className="mb-3">
                  <i className="bi bi-person me-1"></i>
                  {review.is_anonymous ? 'Анонимный пользователь' : `${review.user_first_name} ${review.user_last_name}`}
                </div>
                
                {user && (
                  <div className="d-flex justify-content-md-end align-items-center">
                    <Button 
                      variant={review.user_reaction === 'like' ? 'primary' : 'outline-primary'} 
                      size="sm" 
                      className="me-2 d-flex align-items-center"
                      onClick={() => handleReaction('like')}
                      disabled={isProcessing}
                    >
                      <i className="bi bi-hand-thumbs-up me-1"></i>
                      <span>{review.reaction_stats?.likes || 0}</span>
                    </Button>
                    
                    <Button 
                      variant={review.user_reaction === 'dislike' ? 'danger' : 'outline-danger'} 
                      size="sm"
                      className="d-flex align-items-center"
                      onClick={() => handleReaction('dislike')}
                      disabled={isProcessing}
                    >
                      <i className="bi bi-hand-thumbs-down me-1"></i>
                      <span>{review.reaction_stats?.dislikes || 0}</span>
                    </Button>
                  </div>
                )}
              </div>
            </Col>
          </Row>
          
          {/* Отображение ответов администрации */}
          {review.admin_comments && review.admin_comments.length > 0 && (
            <div className="mt-4">
              <AdminCommentSection comments={review.admin_comments} />
            </div>
          )}
        </Card.Body>
      </Card>
      
      {/* Действия администратора */}
      {isAdmin && (
        <div className="mt-3">
          <AdminReviewActions 
            review={review} 
            onReviewUpdated={setReview} 
          />
        </div>
      )}
    </Container>
  );
};

export default ReviewDetail; 