import React, { memo } from 'react';
import PropTypes from 'prop-types';
import useIntersectionObserver from '../../hooks/useIntersectionObserver';
import './LazyImage.css';

/**
 * Компонент для ленивой загрузки изображений
 * Загружает изображение только когда оно попадает в область видимости
 */
const LazyImage = ({
  src,
  alt,
  width,
  height,
  className = '',
  placeholderSrc = '',
  rootMargin = '100px',
  threshold = 0.1,
  loadingComponent = null,
  onLoad = () => {},
  onError = () => {},
  style = {},
  ...props
}) => {
  // Используем хук Intersection Observer для отслеживания видимости изображения
  const [imageRef, isVisible] = useIntersectionObserver({
    rootMargin,
    threshold,
    triggerOnce: true, // Загружаем изображение только один раз
  });

  // Состояние и обработчики для загрузки изображения
  const [loaded, setLoaded] = React.useState(false);
  const [error, setError] = React.useState(false);

  // Обработчик успешной загрузки изображения
  const handleLoad = (e) => {
    setLoaded(true);
    onLoad(e);
  };

  // Обработчик ошибки загрузки изображения
  const handleError = (e) => {
    setError(true);
    onError(e);
  };

  // Объединение пользовательских стилей с нашими стилями
  const combinedStyle = {
    ...style,
    width: width ? width : 'auto',
    height: height ? height : 'auto',
  };

  // Определяем класс для обертки изображения
  const wrapperClassName = `lazy-image-wrapper ${loaded ? 'loaded' : ''} ${error ? 'error' : ''} ${className}`;

  return (
    <div ref={imageRef} className={wrapperClassName} style={combinedStyle}>
      {/* Показываем placeholder, если изображение не загружено */}
      {!loaded && !error && (
        <div className="lazy-image-placeholder">
          {placeholderSrc ? (
            <img
              src={placeholderSrc}
              alt={alt || 'placeholder'}
              className="placeholder-img"
            />
          ) : loadingComponent ? (
            loadingComponent
          ) : (
            <div className="default-placeholder" />
          )}
        </div>
      )}

      {/* Загружаем изображение только когда оно видимо */}
      {isVisible && (
        <img
          src={src}
          alt={alt || ''}
          className={`lazy-image ${loaded ? 'visible' : ''}`}
          onLoad={handleLoad}
          onError={handleError}
          loading="lazy"
          {...props}
        />
      )}

      {/* Показываем сообщение об ошибке, если загрузка не удалась */}
      {error && (
        <div className="lazy-image-error">
          <span>Ошибка загрузки изображения</span>
        </div>
      )}
    </div>
  );
};

LazyImage.propTypes = {
  src: PropTypes.string.isRequired,
  alt: PropTypes.string,
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  className: PropTypes.string,
  placeholderSrc: PropTypes.string,
  rootMargin: PropTypes.string,
  threshold: PropTypes.number,
  loadingComponent: PropTypes.node,
  onLoad: PropTypes.func,
  onError: PropTypes.func,
  style: PropTypes.object
};

export default memo(LazyImage); 