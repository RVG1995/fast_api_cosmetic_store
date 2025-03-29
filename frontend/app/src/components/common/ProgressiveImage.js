import React, { useState, useEffect, useCallback } from 'react';
import '../../styles/ProgressiveImage.css';

const ProgressiveImage = ({ src, alt, className, lowResSrc, aspectRatio = '1:1', style = {}, placeholderClassName }) => {
  const [imgSrc, setImgSrc] = useState(lowResSrc || null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(false);
  
  // Создаем функцию загрузки изображения, которую можно повторно вызвать при ошибке
  const loadImage = useCallback(() => {
    // Сбросить состояние
    setIsLoaded(false);
    setError(false);
    
    // Если src пустой или null, установить ошибку
    if (!src) {
      console.warn('ProgressiveImage: src не указан');
      setError(true);
      setIsLoaded(true);
      return;
    }
    
    // Для журналирования
    console.log(`ProgressiveImage: Загрузка ${src}`);
    
    const img = new Image();
    
    // Установить заголовки CORS
    img.crossOrigin = 'anonymous';
    
    img.onload = () => {
      console.log(`ProgressiveImage: Успешно загружено ${src}`);
      setImgSrc(src);
      setIsLoaded(true);
    };
    
    img.onerror = (e) => {
      console.error(`ProgressiveImage: Ошибка загрузки ${src}`, e);
      setError(true);
      setIsLoaded(true);
    };
    
    // Начать загрузку после установки обработчиков
    img.src = src;
    
    // Возвращаем функцию очистки
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);
  
  // Эффект для загрузки изображения при изменении src
  useEffect(() => {
    if (src !== imgSrc) {
      return loadImage();
    }
  }, [src, imgSrc, loadImage]);
  
  // Преобразование соотношения сторон в проценты для padding-bottom
  const getPaddingBottom = () => {
    if (aspectRatio) {
      const [width, height] = aspectRatio.split(':').map(Number);
      return `${(height / width) * 100}%`;
    }
    return '100%'; // По умолчанию квадрат
  };
  
  const containerStyle = {
    paddingBottom: getPaddingBottom(),
    ...style
  };
  
  // Обработчик повторной загрузки при ошибке
  const handleRetry = () => {
    loadImage();
  };
  
  return (
    <div className={`progressive-image-container ${className || ''}`} style={containerStyle}>
      {!isLoaded && <div className={`image-skeleton ${placeholderClassName || ''}`}></div>}
      {error ? (
        <div className="image-error" onClick={handleRetry}>
          <span>⚠️</span>
          <p>Не удалось загрузить изображение</p>
        </div>
      ) : (
        <img 
          src={imgSrc || src} 
          alt={alt}
          className={`progressive-image ${isLoaded ? 'loaded' : 'loading'}`}
          loading="lazy"
          onError={handleRetry}
        />
      )}
    </div>
  );
};

export default ProgressiveImage; 