import React, { useState, useEffect } from 'react';
import { Form, Button, Card, Alert, Spinner } from 'react-bootstrap';
import { reviewAPI } from '../../utils/api';
import StarRating from './StarRating';
import { useAuth } from '../../context/AuthContext';

const ReviewForm = ({ 
  productId = null, 
  productName = null, 
  onReviewSubmitted 
}) => {
  const [reviewData, setReviewData] = useState({
    rating: 0,
    content: '',
    is_anonymous: false
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const { isAuthenticated } = useAuth();
  const [permissions, setPermissions] = useState({
    canReviewProduct: false,
    canReviewStore: false,
    hasReviewedProduct: false,
    hasReviewedStore: false
  });

  useEffect(() => {
    // Проверяем права на оставление отзыва при монтировании компонента
    const checkPermissions = async () => {
      try {
        console.log('Запрашиваем права на отзыв, productId:', productId);
        const response = await reviewAPI.checkReviewPermissions(productId);
        console.log('Получен ответ о правах:', response.data);
        setPermissions(response.data);
        console.log('Обновлено состояние permissions:', response.data);
      } catch (error) {
        console.error('Ошибка при проверке прав на оставление отзыва:', error);
        setError('Не удалось проверить возможность оставления отзыва');
      }
    };

    checkPermissions();
  }, [productId]);

  // Обработчик изменения значения поля
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setReviewData({
      ...reviewData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  // Обработчик изменения рейтинга
  const handleRatingChange = (newRating) => {
    setReviewData({ ...reviewData, rating: newRating });
  };

  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Сбрасываем предыдущие сообщения
    setError(null);
    setSuccess(false);
    
    // Проверяем, что пользователь выбрал рейтинг
    if (reviewData.rating === 0) {
      setError('Пожалуйста, укажите рейтинг');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const submitData = {
        rating: reviewData.rating,
        content: reviewData.content.trim(),
        is_anonymous: reviewData.is_anonymous
      };
      
      // Определяем, какой тип отзыва добавить
      if (productId) {
        // Отзыв о товаре
        await reviewAPI.createProductReview(productId, submitData);
      } else {
        // Отзыв о магазине
        await reviewAPI.createStoreReview(submitData);
      }
      
      // Отображаем сообщение об успехе
      setSuccess(true);
      
      // Сбрасываем форму
      setReviewData({
        rating: 0,
        content: '',
        is_anonymous: false
      });
      
      // Вызываем колбэк успешного добавления
      if (onReviewSubmitted) {
        onReviewSubmitted();
      }
    } catch (error) {
      console.error('Ошибка при добавлении отзыва:', error);
      
      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError('Произошла ошибка при добавлении отзыва. Пожалуйста, попробуйте позже.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Проверяем, может ли пользователь оставить отзыв
  const canSubmitProductReview = productId && permissions.can_review_product && !permissions.has_reviewed_product;
  const canSubmitStoreReview = !productId && permissions.can_review_store && !permissions.has_reviewed_store;
  
  console.log('Текущие разрешения:', { 
    permissions, 
    productId, 
    canSubmitProductReview, 
    canSubmitStoreReview
  });

  // Если пользователь не может оставить отзыв, показываем сообщение
  if (productId && !canSubmitProductReview) {
    if (permissions.has_reviewed_product) {
      return (
        <Alert variant="info">
          Вы уже оставили отзыв на этот товар. Спасибо за ваш отзыв!
        </Alert>
      );
    } else if (!permissions.can_review_product) {
      return (
        <Alert variant="warning">
          Для оставления отзыва на этот товар вам необходимо приобрести его и получить заказ.
        </Alert>
      );
    }
  }
  
  if (!productId && !canSubmitStoreReview) {
    if (permissions.has_reviewed_store) {
      return (
        <Alert variant="info">
          Вы уже оставили отзыв о нашем магазине. Спасибо за ваш отзыв!
        </Alert>
      );
    } else if (!permissions.can_review_store) {
      return (
        <Alert variant="warning">
          Для оставления отзыва о магазине вам необходимо совершить хотя бы одну покупку и получить заказ.
        </Alert>
      );
    }
  }

  if (!isAuthenticated) {
    return (
      <Card className="shadow-sm mb-4">
        <Card.Header className="bg-light">
          <h5 className="mb-0">Оставить отзыв</h5>
        </Card.Header>
        <Card.Body>
          <Alert variant="info">
            Для того чтобы оставить отзыв, необходимо 
            <Button 
              variant="link" 
              href="/login"
              className="p-0 mx-1 align-baseline"
            >
              войти в аккаунт
            </Button>
          </Alert>
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm mb-4">
      <Card.Header className="bg-primary text-white">
        <h5 className="mb-0">
          {productId 
            ? `Оставить отзыв о товаре: ${productName}` 
            : 'Оставить отзыв о магазине'}
        </h5>
      </Card.Header>
      <Card.Body>
        {success && (
          <Alert variant="success" onClose={() => setSuccess(false)} dismissible>
            Ваш отзыв успешно добавлен! Благодарим за обратную связь.
          </Alert>
        )}

        {error && (
          <Alert variant="danger" onClose={() => setError(null)} dismissible>
            {error}
          </Alert>
        )}

        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Ваша оценка</Form.Label>
            <div>
              <StarRating 
                initialRating={reviewData.rating} 
                onRatingChange={handleRatingChange} 
              />
            </div>
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Ваш комментарий</Form.Label>
            <Form.Control
              as="textarea"
              rows={4}
              name="content"
              value={reviewData.content}
              onChange={handleInputChange}
              placeholder="Расскажите о вашем опыте (необязательно)"
            />
          </Form.Group>
          
          <Form.Group className="mb-3">
            <Form.Check 
              type="checkbox"
              id="anonymousReview"
              name="is_anonymous"
              label="Оставить отзыв анонимно"
              checked={reviewData.is_anonymous}
              onChange={handleInputChange}
            />
            <Form.Text className="text-muted">
              Если выбрано, ваше имя не будет отображаться рядом с отзывом
            </Form.Text>
          </Form.Group>

          <div className="d-grid gap-2">
            <Button 
              variant="primary" 
              type="submit" 
              disabled={isSubmitting || reviewData.rating === 0}
            >
              {isSubmitting ? (
                <>
                  <Spinner
                    as="span"
                    animation="border"
                    size="sm"
                    role="status"
                    aria-hidden="true"
                    className="me-2"
                  />
                  Отправка...
                </>
              ) : 'Отправить отзыв'}
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
};

export default ReviewForm; 