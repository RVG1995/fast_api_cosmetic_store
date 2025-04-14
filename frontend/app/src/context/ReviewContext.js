import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { reviewAPI } from '../utils/api';

// Создаем контекст для управления рейтингами товаров
const ReviewContext = createContext();

export const useReviews = () => useContext(ReviewContext);

export const ReviewProvider = ({ children }) => {
  // Состояние для хранения рейтингов товаров
  const [productRatings, setProductRatings] = useState({});
  const [loadingRatings, setLoadingRatings] = useState(false);

  // Функция для получения рейтингов нескольких товаров
  const fetchBatchProductRatings = useCallback(async (productIds) => {
    if (!productIds || productIds.length === 0) return;
    
    // Фильтруем только те товары, которые еще не загружены
    const unloadedProductIds = productIds.filter(id => !productRatings[id]);
    
    if (unloadedProductIds.length === 0) return;
    
    setLoadingRatings(true);
    try {
      const response = await reviewAPI.getBatchProductStats(unloadedProductIds);
      
      if (response.data && response.data.results) {
        setProductRatings(prev => {
          const newRatings = { ...prev };
          
          // Добавляем новые рейтинги из ответа
          Object.entries(response.data.results).forEach(([id, data]) => {
            newRatings[id] = {
              average_rating: data.average_rating,
              total_reviews: data.total_reviews,
              rating_counts: data.rating_counts
            };
          });
          
          return newRatings;
        });
      }
    } catch (error) {
      console.error('Ошибка при получении рейтингов товаров:', error);
    } finally {
      setLoadingRatings(false);
    }
  }, [productRatings]);

  // Функция для получения рейтинга одного товара
  const getProductRating = useCallback((productId) => {
    if (!productId) return null;
    
    return productRatings[productId] || null;
  }, [productRatings]);

  // Функция для инвалидации кэша рейтинга конкретного товара
  const invalidateProductRating = useCallback(async (productId) => {
    if (!productId) return;
    
    console.log(`Инвалидация кэша рейтинга для товара ${productId}`);
    
    try {
      // Запрос актуальных данных
      const response = await reviewAPI.getProductStats(productId);
      
      if (response.data) {
        console.log(`Получены новые данные о рейтинге товара ${productId}:`, response.data);
        
        // Обновляем только данные для конкретного товара
        setProductRatings(prev => {
          const newRatings = { ...prev };
          newRatings[productId] = {
            average_rating: response.data.average_rating,
            total_reviews: response.data.total_reviews,
            rating_counts: response.data.rating_counts
          };
          return newRatings;
        });
      }
    } catch (error) {
      console.error(`Ошибка при инвалидации рейтинга товара ${productId}:`, error);
    }
  }, []);

  // Значение контекста
  const value = {
    productRatings,
    loadingRatings,
    fetchBatchProductRatings,
    getProductRating,
    invalidateProductRating
  };

  return (
    <ReviewContext.Provider value={value}>
      {children}
    </ReviewContext.Provider>
  );
};

export default ReviewContext;