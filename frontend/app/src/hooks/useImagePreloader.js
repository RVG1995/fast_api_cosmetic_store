import { useState, useEffect, useCallback } from 'react';

/**
 * Хук для предварительной загрузки изображений
 * Позволяет заранее загрузить изображения для улучшения пользовательского опыта
 * 
 * @param {string[]} imageUrls - Массив URL-адресов изображений для загрузки
 * @param {boolean} loadImmediately - Начать загрузку сразу (по умолчанию true)
 * @returns {Object} Объект с состоянием загрузки и функциями управления
 */
function useImagePreloader(imageUrls = [], loadImmediately = true) {
  // Состояние загруженных изображений (Map с ключами URL и значениями объекта состояния)
  const [imagesMap, setImagesMap] = useState(new Map());
  
  // Общее состояние загрузки
  const [status, setStatus] = useState({
    loading: false,
    loaded: 0,
    total: imageUrls.length,
    completed: false,
    error: null
  });

  // Функция для загрузки одного изображения
  const loadImage = useCallback((url) => {
    return new Promise((resolve, reject) => {
      // Если URL уже в состоянии "loaded", просто возвращаем успех
      if (imagesMap.get(url)?.status === 'loaded') {
        resolve({ url, status: 'loaded' });
        return;
      }
      
      // Обновляем состояние URL на "loading"
      setImagesMap(prev => {
        const newMap = new Map(prev);
        newMap.set(url, { status: 'loading', error: null });
        return newMap;
      });
      
      // Создаем изображение и устанавливаем обработчики
      const img = new Image();
      
      img.onload = () => {
        setImagesMap(prev => {
          const newMap = new Map(prev);
          newMap.set(url, { status: 'loaded', error: null });
          return newMap;
        });
        resolve({ url, status: 'loaded' });
      };
      
      img.onerror = (error) => {
        const errorMessage = `Failed to load image: ${url}`;
        setImagesMap(prev => {
          const newMap = new Map(prev);
          newMap.set(url, { status: 'error', error: errorMessage });
          return newMap;
        });
        reject({ url, status: 'error', error: errorMessage });
      };
      
      // Начинаем загрузку
      img.src = url;
    });
  }, [imagesMap]);

  // Функция для загрузки всех изображений
  const loadAllImages = useCallback(async () => {
    if (imageUrls.length === 0) {
      setStatus({
        loading: false,
        loaded: 0,
        total: 0,
        completed: true,
        error: null
      });
      return;
    }
    
    // Обновляем начальное состояние загрузки
    setStatus(prev => ({
      ...prev,
      loading: true,
      loaded: 0,
      total: imageUrls.length,
      completed: false,
      error: null
    }));
    
    // Загружаем все изображения параллельно
    const promises = imageUrls.map(url => 
      loadImage(url)
        .then(() => {
          setStatus(prev => ({
            ...prev,
            loaded: prev.loaded + 1
          }));
        })
        .catch((error) => {
          console.error('Error loading image:', error);
          setStatus(prev => ({
            ...prev,
            error: `Failed to load one or more images`
          }));
        })
    );
    
    try {
      await Promise.all(promises);
      setStatus(prev => ({
        ...prev,
        loading: false,
        completed: true
      }));
    } catch (error) {
      console.error('Error during image preloading:', error);
      setStatus(prev => ({
        ...prev,
        loading: false,
        completed: true,
        error: 'Failed to preload images'
      }));
    }
  }, [imageUrls, loadImage]);

  // Немедленно начинаем загрузку, если указан флаг loadImmediately
  useEffect(() => {
    if (loadImmediately) {
      loadAllImages();
    }
  }, [loadImmediately, loadAllImages]);

  // Вычисляем прогресс загрузки
  const progress = status.total > 0 
    ? Math.round((status.loaded / status.total) * 100) 
    : 100;

  return {
    ...status,
    progress,
    imagesMap,
    loadImage,
    loadAllImages,
    // Удобные геттеры статуса изображений
    getImageStatus: (url) => imagesMap.get(url)?.status || 'idle',
    isImageLoaded: (url) => imagesMap.get(url)?.status === 'loaded',
    isImageLoading: (url) => imagesMap.get(url)?.status === 'loading',
    isImageError: (url) => imagesMap.get(url)?.status === 'error',
    getImageError: (url) => imagesMap.get(url)?.error || null
  };
}

export default useImagePreloader; 