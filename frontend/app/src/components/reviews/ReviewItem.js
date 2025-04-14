import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Badge, Button } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { reviewAPI } from '../../utils/api';
import { formatDate } from '../../utils/helpers';
import AdminCommentSection from './AdminCommentSection';
import AdminReviewActions from './AdminReviewActions';
import { useAuth } from '../../context/AuthContext';

const ReviewItem = ({ review, onReactionChange, isAdmin = false }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [localReview, setLocalReview] = useState(review);
  const { user } = useAuth();

  // Обновлять localReview когда изменяется внешний review
  useEffect(() => {
    if (review) {
      setLocalReview(review);
    }
  }, [review]);

  // Проверяем, что все необходимые данные доступны
  if (!localReview || typeof localReview !== 'object') {
    console.error('ReviewItem: localReview отсутствует или не является объектом', localReview);
    return null;
  }

  // Обработка реакции (лайк/дизлайк)
  const handleReaction = async (reactionType) => {
    if (isProcessing || !user) return;
    
    setIsProcessing(true);
    try {
      const currentReaction = localReview.user_reaction;
      console.log(`Начало обработки реакции: ${reactionType}, текущая реакция: ${currentReaction}, 
        текущие счетчики: likes=${localReview.reaction_stats?.likes || 0}, dislikes=${localReview.reaction_stats?.dislikes || 0}`);
      
      let response;
      
      // Если текущая реакция такая же, как нажатая кнопка - удаляем её
      if (currentReaction === reactionType) {
        console.log(`Отправляем запрос на удаление реакции ${reactionType} для отзыва ${localReview.id}`);
        response = await reviewAPI.deleteReaction(localReview.id);
        console.log('Ответ на запрос удаления реакции:', response);
      } 
      // Иначе - добавляем новую реакцию (или изменяем существующую)
      else {
        console.log(`Отправляем запрос на добавление реакции ${reactionType} для отзыва ${localReview.id}`);
        response = await reviewAPI.addReaction(localReview.id, reactionType);
        console.log('Ответ на запрос добавления реакции:', response);
      }
      
      // Проверяем ответ
      if (!response) {
        console.error('Не получены данные от API при обработке реакции');
        return;
      }
      
      // Создаем новый объект отзыва с данными от сервера
      const updatedReview = {
        ...localReview,
        reaction_stats: {
          likes: response.reaction_stats?.likes || 0,
          dislikes: response.reaction_stats?.dislikes || 0
        },
        user_reaction: response.user_reaction
      };
      
      console.log(`Обновление после запроса. Новые счетчики: likes=${updatedReview.reaction_stats.likes}, 
        dislikes=${updatedReview.reaction_stats.dislikes}, пользовательская реакция: ${updatedReview.user_reaction}`);
      
      // Обновляем локальное состояние
      setLocalReview(updatedReview);
      
      // Уведомляем родительский компонент
      if (onReactionChange) {
        console.log('Отправляем обновление в родительский компонент');
        onReactionChange(updatedReview);
      }
    } catch (error) {
      console.error('Ошибка при обработке реакции:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Обработчик обновления отзыва (вызывается из AdminReviewActions)
  const handleReviewUpdate = (updatedReview) => {
    if (!updatedReview) {
      console.error('handleReviewUpdate получил undefined или null updatedReview');
      return;
    }
    
    console.log('Получено обновление отзыва от AdminReviewActions:', updatedReview);
    
    // Сохраняем существующие поля, если они отсутствуют в ответе API
    const mergedReview = {
      ...localReview,
      ...updatedReview,
      // Если в ответе нет полей для отображения, используем существующие
      rating: updatedReview.rating || localReview.rating,
      product_name: updatedReview.product_name || localReview.product_name,
      product_id: updatedReview.product_id || localReview.product_id,
      admin_comments: updatedReview.admin_comments || localReview.admin_comments,
      user_first_name: updatedReview.user_first_name || localReview.user_first_name,
      user_last_name: updatedReview.user_last_name || localReview.user_last_name,
      is_anonymous: updatedReview.is_anonymous === undefined ? localReview.is_anonymous : updatedReview.is_anonymous,
      is_hidden: updatedReview.is_hidden === undefined ? localReview.is_hidden : updatedReview.is_hidden,
      created_at: updatedReview.created_at || localReview.created_at,
      reaction_stats: updatedReview.reaction_stats || localReview.reaction_stats,
      user_reaction: updatedReview.user_reaction === undefined ? localReview.user_reaction : updatedReview.user_reaction
    };
    
    console.log('Обновленный отзыв после объединения с существующими данными:', mergedReview);
    
    setLocalReview(mergedReview);
    
    if (onReactionChange) {
      onReactionChange(mergedReview);
    }
  };

  // Форматирование для отображения звезд рейтинга
  const renderStars = (rating = 0) => {
    const stars = [];
    const ratingValue = typeof rating === 'number' ? rating : 0;
    
    for (let i = 0; i < 5; i++) {
      stars.push(
        <i 
          key={i} 
          className={i < ratingValue ? 'bi bi-star-fill text-warning' : 'bi bi-star text-muted'}
        />
      );
    }
    return stars;
  };

  // Безопасное получение значений с проверкой на undefined/null
  const rating = localReview.rating || 0;
  const productName = localReview.product_name || '';
  const productId = localReview.product_id || 0;
  const content = localReview.content || '';
  const createdAt = localReview.created_at || '';
  const isAnonymous = localReview.is_anonymous || false;
  const reviewUserId = localReview.user_id;
  const firstName = localReview.user_first_name || 'Пользователь';
  const lastName = localReview.user_last_name || '';
  const isHidden = localReview.is_hidden || false;
  const userReaction = localReview.user_reaction || '';
  const reactionStats = localReview.reaction_stats || { likes: 0, dislikes: 0 };
  const adminComments = localReview.admin_comments || [];
  
  // Проверяем, является ли текущий пользователь автором отзыва
  const isCurrentUserAuthor = user && reviewUserId && user.id === reviewUserId;

  return (
    <Card className="mb-3 shadow-sm">
      <Card.Body>
        <Row>
          <Col md={8}>
            <div className="d-flex align-items-center mb-2">
              {renderStars(rating)}
              <span className="ms-2 fw-bold">{rating}/5</span>
              
              {isHidden && (
                <Badge bg="secondary" className="ms-3">
                  <i className="bi bi-eye-slash me-1"></i>
                  Скрыт
                </Badge>
              )}
            </div>
            
            <h5 className="mb-3">
              {productName && (
                <Link to={`/product/${productId}`} className="text-decoration-none">
                  {productName}
                </Link>
              )}
            </h5>
            
            <p className="mb-1">{content}</p>
          </Col>
          
          <Col md={4}>
            <div className="text-md-end">
              <div className="text-muted mb-2">
                <i className="bi bi-calendar me-1"></i>
                {formatDate(createdAt)}
              </div>
              
              <div className="mb-3">
                <i className="bi bi-person me-1"></i>
                {isAnonymous 
                  ? (isCurrentUserAuthor 
                      ? <span>Ваш отзыв <Badge bg="info" className="ms-1">анонимный для других</Badge></span>
                      : 'Анонимный пользователь')
                  : `${firstName} ${lastName}`}
              </div>
              
              <div className="d-flex justify-content-md-end align-items-center">
                <Button 
                  variant={userReaction === 'like' ? 'primary' : 'outline-primary'} 
                  size="sm" 
                  className="me-2 d-flex align-items-center"
                  onClick={() => handleReaction('like')}
                  disabled={isProcessing || !user}
                >
                  <i className="bi bi-hand-thumbs-up me-1"></i>
                  <span>{reactionStats?.likes || 0}</span>
                </Button>
                
                <Button 
                  variant={userReaction === 'dislike' ? 'danger' : 'outline-danger'} 
                  size="sm"
                  className="d-flex align-items-center"
                  onClick={() => handleReaction('dislike')}
                  disabled={isProcessing || !user}
                >
                  <i className="bi bi-hand-thumbs-down me-1"></i>
                  <span>{reactionStats?.dislikes || 0}</span>
                </Button>
              </div>
            </div>
          </Col>
        </Row>
        
        {/* Отображение ответов администрации */}
        {adminComments.length > 0 && (
          <div className="mt-3">
            <AdminCommentSection comments={adminComments} />
          </div>
        )}
        
        {/* Действия администратора */}
        {isAdmin && (
          <div className="mt-3 border-top pt-3">
            <AdminReviewActions 
              review={localReview} 
              onReviewUpdated={handleReviewUpdate} 
            />
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default ReviewItem; 