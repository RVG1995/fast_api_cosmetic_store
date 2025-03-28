import React, { useState } from 'react';
import { Button, Card, Form, Alert, Modal } from 'react-bootstrap';
import { reviewAPI } from '../../utils/api';

const AdminReviewActions = ({ review, onReviewUpdated }) => {
  const [showCommentModal, setShowCommentModal] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Обработчик открытия/закрытия модального окна
  const handleToggleModal = () => {
    setShowCommentModal(!showCommentModal);
    setCommentText('');
    setError(null);
    setSuccess(null);
  };

  // Обработчик изменения скрытия отзыва
  const handleToggleVisibility = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const updatedReview = await reviewAPI.admin.toggleReviewVisibility(review.id);
      
      if (onReviewUpdated) {
        onReviewUpdated(updatedReview);
      }
      
      setSuccess(`Отзыв ${updatedReview.is_hidden ? 'скрыт' : 'возвращен к отображению'}`);
      
      // Скрываем сообщение через 3 секунды
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (error) {
      console.error('Ошибка при изменении видимости отзыва:', error);
      setError('Не удалось изменить видимость отзыва');
    } finally {
      setIsLoading(false);
    }
  };

  // Обработчик отправки комментария
  const handleSubmitComment = async () => {
    // Проверяем, что текст комментария не пустой
    if (!commentText.trim()) {
      setError('Пожалуйста, введите текст комментария');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedReview = await reviewAPI.admin.addComment(review.id, commentText.trim());
      
      console.log('Обновленный отзыв после добавления комментария:', updatedReview);
      
      // Обновляем данные в родительском компоненте
      if (onReviewUpdated) {
        onReviewUpdated(updatedReview);
      }
      
      // Закрываем модальное окно и сбрасываем форму
      setCommentText('');
      setShowCommentModal(false);
      
      // Показываем сообщение об успехе
      setSuccess('Комментарий администратора добавлен');
      
      // Скрываем сообщение через 3 секунды
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (error) {
      console.error('Ошибка при добавлении комментария:', error);
      setError('Не удалось добавить комментарий');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="bg-light">
      <Card.Body className="py-2">
        {error && <Alert variant="danger">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}
        
        <div className="d-flex flex-wrap">
          <Button
            variant={review.is_hidden ? 'outline-success' : 'outline-danger'}
            size="sm"
            className="me-2 mb-2"
            onClick={handleToggleVisibility}
            disabled={isLoading}
          >
            <i 
              className={`bi ${review.is_hidden ? 'bi-eye' : 'bi-eye-slash'} me-1`}
            />
            {review.is_hidden ? 'Показать отзыв' : 'Скрыть отзыв'}
          </Button>
          
          <Button
            variant="outline-primary"
            size="sm"
            className="me-2 mb-2"
            onClick={handleToggleModal}
            disabled={isLoading}
          >
            <i className="bi bi-chat me-1"></i>
            Добавить комментарий
          </Button>
        </div>
      </Card.Body>
      
      {/* Модальное окно для добавления комментария */}
      <Modal show={showCommentModal} onHide={handleToggleModal}>
        <Modal.Header closeButton>
          <Modal.Title>Добавить комментарий администратора</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label>Текст комментария</Form.Label>
            <Form.Control
              as="textarea"
              rows={4}
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Введите ответ на отзыв..."
              maxLength={1000}
            />
            <Form.Text className="text-muted">
              Максимум 1000 символов
            </Form.Text>
          </Form.Group>
          
          {error && <Alert variant="danger">{error}</Alert>}
        </Modal.Body>
        <Modal.Footer>
          <Button 
            variant="secondary" 
            onClick={handleToggleModal}
            disabled={isLoading}
          >
            <i className="bi bi-x me-1"></i>
            Отмена
          </Button>
          <Button 
            variant="primary" 
            onClick={handleSubmitComment}
            disabled={isLoading || !commentText.trim()}
          >
            <i className="bi bi-check me-1"></i>
            {isLoading ? 'Отправка...' : 'Отправить'}
          </Button>
        </Modal.Footer>
      </Modal>
    </Card>
  );
};

export default AdminReviewActions; 