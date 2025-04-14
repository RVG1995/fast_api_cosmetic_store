import React, { useState, useEffect } from 'react';
import { Pagination, Alert, Spinner } from 'react-bootstrap';
import { reviewAPI } from '../../utils/api';
import ReviewItem from './ReviewItem';
import { useAuth } from '../../context/AuthContext';

const ReviewList = ({ productId = null, showStats = false, isAdminView = false }) => {
  const [reviews, setReviews] = useState([]);
  const [totalReviews, setTotalReviews] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin, user } = useAuth();

  const pageSize = 5; // Количество отзывов на странице

  useEffect(() => {
    const fetchReviews = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Определяем, какие отзывы загружать (для товара или для магазина)
        let response;
        
        // В админке всегда используем админский API для получения всех отзывов
        if (isAdminView) {
          if (productId) {
            response = await reviewAPI.admin.getProductReviews(productId, currentPage, pageSize);
          } else {
            response = await reviewAPI.admin.getStoreReviews(currentPage, pageSize);
          }
        } else {
          // На клиентской части используем обычный API
          if (productId) {
            response = await reviewAPI.getProductReviews(productId, currentPage, pageSize);
          } else {
            response = await reviewAPI.getStoreReviews(currentPage, pageSize);
          }
        }
        
        console.log('ReviewList: Получены отзывы с сервера:', response.data);
        setReviews(response.data.items);
        setTotalReviews(response.data.total);
        setTotalPages(response.data.pages);
      } catch (error) {
        console.error('Ошибка при загрузке отзывов:', error);
        setError('Не удалось загрузить отзывы. Пожалуйста, попробуйте позже.');
      } finally {
        setIsLoading(false);
      }
    };

    console.log('ReviewList: Загружаем отзывы для', { productId, currentPage, isAdmin, user, isAdminView });
    fetchReviews();
  }, [productId, currentPage, isAdmin, user, isAdminView]);

  // Обработчик изменения страницы
  const handlePageChange = (page) => {
    setCurrentPage(page);
    window.scrollTo(0, 0);
  };

  // Обработчик обновления отзыва после реакции
  const handleReviewUpdate = (updatedReview) => {
    console.log('ReviewList: Получено обновление отзыва:', updatedReview);
    
    if (!updatedReview || !updatedReview.id) {
      console.error('ReviewList: Получен некорректный updatedReview:', updatedReview);
      return;
    }
    
    // Находим индекс отзыва в массиве
    const reviewIndex = reviews.findIndex(review => review.id === updatedReview.id);
    
    if (reviewIndex === -1) {
      console.error(`ReviewList: Отзыв с id=${updatedReview.id} не найден в списке`);
      return;
    }
    
    console.log(`ReviewList: Обновляем отзыв на позиции ${reviewIndex}`);
    
    // Создаем новый массив с обновленным отзывом
    const updatedReviews = [...reviews];
    updatedReviews[reviewIndex] = updatedReview;
    
    // Обновляем состояние
    setReviews(updatedReviews);
    console.log('ReviewList: Список отзывов обновлен', updatedReviews);
  };

  // Компонент пагинации
  const renderPagination = () => {
    if (totalPages <= 1) return null;
    
    const items = [];
    const maxVisiblePages = 5;
    const halfVisible = Math.floor(maxVisiblePages / 2);
    
    let startPage = Math.max(1, currentPage - halfVisible);
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    // Кнопка "Предыдущая"
    items.push(
      <Pagination.Prev 
        key="prev" 
        onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
        disabled={currentPage === 1}
      />
    );
    
    // Первая страница и многоточие
    if (startPage > 1) {
      items.push(
        <Pagination.Item 
          key={1} 
          onClick={() => handlePageChange(1)}
        >
          1
        </Pagination.Item>
      );
      if (startPage > 2) {
        items.push(<Pagination.Ellipsis key="ellipsis1" />);
      }
    }
    
    // Видимые страницы
    for (let page = startPage; page <= endPage; page++) {
      items.push(
        <Pagination.Item 
          key={page} 
          active={page === currentPage}
          onClick={() => handlePageChange(page)}
        >
          {page}
        </Pagination.Item>
      );
    }
    
    // Последняя страница и многоточие
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        items.push(<Pagination.Ellipsis key="ellipsis2" />);
      }
      items.push(
        <Pagination.Item 
          key={totalPages} 
          onClick={() => handlePageChange(totalPages)}
        >
          {totalPages}
        </Pagination.Item>
      );
    }
    
    // Кнопка "Следующая"
    items.push(
      <Pagination.Next 
        key="next" 
        onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
        disabled={currentPage === totalPages}
      />
    );
    
    return (
      <Pagination className="justify-content-center my-4">
        {items}
      </Pagination>
    );
  };

  return (
    <div className="reviews-wrapper">
      {/* Заголовок с количеством отзывов */}
      {showStats && totalReviews > 0 && (
        <div className="reviews-count mb-3">
          <strong>
            {productId ? 'Отзывы о товаре' : 'Отзывы о магазине'} ({totalReviews})
          </strong>
        </div>
      )}
      
      {isLoading ? (
        <div className="text-center my-4">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2">Загрузка отзывов...</p>
        </div>
      ) : error ? (
        <Alert variant="danger">{error}</Alert>
      ) : reviews.length === 0 ? (
        <Alert variant="info">
          {productId 
            ? 'Для этого товара пока нет отзывов. Будьте первым, кто оставит отзыв!' 
            : 'Для магазина пока нет отзывов. Будьте первым, кто оставит отзыв!'}
        </Alert>
      ) : (
        <div className="reviews-list">
          {reviews.map(review => (
            <ReviewItem 
              key={review.id} 
              review={review} 
              onReactionChange={handleReviewUpdate}
              isAdmin={isAdminView ? true : (user && isAdmin)}
            />
          ))}
        </div>
      )}
      
      {renderPagination()}
    </div>
  );
};

export default ReviewList; 