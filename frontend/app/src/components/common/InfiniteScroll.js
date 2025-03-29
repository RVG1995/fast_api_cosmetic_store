import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import useIntersectionObserver from '../../hooks/useIntersectionObserver';

/**
 * Компонент для реализации бесконечной прокрутки (infinite scroll)
 * Загружает новые данные при прокрутке страницы до конца текущего контента
 */
const InfiniteScroll = ({
  children,
  onLoadMore,
  hasMore = false,
  loading = false,
  loadingComponent = null,
  endMessageComponent = null,
  rootMargin = '100px',
  threshold = 0.1,
  className = '',
  style = {}
}) => {
  // Используем хук Intersection Observer для отслеживания видимости триггера
  const [loadMoreRef, isVisible] = useIntersectionObserver({
    rootMargin,
    threshold,
  });

  // Вызываем onLoadMore, когда триггер становится видимым и есть еще данные для загрузки
  useEffect(() => {
    if (isVisible && hasMore && !loading) {
      onLoadMore();
    }
  }, [isVisible, hasMore, loading, onLoadMore]);

  return (
    <div className={className} style={style}>
      {children}
      
      {loading && loadingComponent}
      
      {!hasMore && !loading && endMessageComponent}
      
      {/* Триггер загрузки, становится видимым при прокрутке вниз */}
      {hasMore && (
        <div ref={loadMoreRef} style={{ height: '20px', margin: '10px 0' }}>
          {/* Пустой элемент для отслеживания прокрутки */}
        </div>
      )}
    </div>
  );
};

InfiniteScroll.propTypes = {
  children: PropTypes.node.isRequired,
  onLoadMore: PropTypes.func.isRequired,
  hasMore: PropTypes.bool,
  loading: PropTypes.bool,
  loadingComponent: PropTypes.node,
  endMessageComponent: PropTypes.node,
  rootMargin: PropTypes.string,
  threshold: PropTypes.number,
  className: PropTypes.string,
  style: PropTypes.object
};

export default InfiniteScroll; 