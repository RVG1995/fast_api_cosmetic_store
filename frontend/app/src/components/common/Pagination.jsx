import React, { memo, useMemo } from 'react';
import { Pagination as BSPagination } from 'react-bootstrap';
import PropTypes from 'prop-types';

/**
 * Компонент пагинации для навигации по страницам
 * @param {Object} props - Свойства компонента
 * @param {number} props.currentPage - Текущая страница
 * @param {number} props.totalPages - Общее количество страниц
 * @param {function} props.onPageChange - Обработчик изменения страницы
 * @param {number} props.maxVisiblePages - Максимальное количество видимых кнопок страниц
 * @param {string} props.className - Дополнительные CSS классы
 */
const Pagination = memo(({ 
  currentPage, 
  totalPages, 
  onPageChange, 
  maxVisiblePages = 5,
  className = ''
}) => {
  // Вычисляем видимые страницы на основе текущей страницы и общего количества
  const visiblePages = useMemo(() => {
    // Если страниц меньше или равно максимальному количеству видимых, показываем все
    if (totalPages <= maxVisiblePages) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    
    // Вычисляем начальную и конечную страницы для отображения
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = startPage + maxVisiblePages - 1;
    
    // Корректируем, если выходим за пределы
    if (endPage > totalPages) {
      endPage = totalPages;
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    return Array.from({ length: endPage - startPage + 1 }, (_, i) => startPage + i);
  }, [currentPage, totalPages, maxVisiblePages]);
  
  // Если всего одна страница, не показываем пагинацию
  if (totalPages <= 1) {
    return null;
  }
  
  // Обработчик клика по странице
  const handlePageClick = (page) => {
    if (page !== currentPage) {
      onPageChange(page);
    }
  };
  
  return (
    <BSPagination className={className}>
      {/* Кнопка "Предыдущая" */}
      <BSPagination.Prev 
        onClick={() => handlePageClick(currentPage - 1)}
        disabled={currentPage === 1}
      />
      
      {/* Кнопка первой страницы и эллипсис, если нужно */}
      {visiblePages[0] > 1 && (
        <>
          <BSPagination.Item 
            onClick={() => handlePageClick(1)}
            active={currentPage === 1}
          >
            1
          </BSPagination.Item>
          {visiblePages[0] > 2 && <BSPagination.Ellipsis disabled />}
        </>
      )}
      
      {/* Видимые страницы */}
      {visiblePages.map(page => (
        <BSPagination.Item
          key={page}
          active={page === currentPage}
          onClick={() => handlePageClick(page)}
        >
          {page}
        </BSPagination.Item>
      ))}
      
      {/* Кнопка последней страницы и эллипсис, если нужно */}
      {visiblePages[visiblePages.length - 1] < totalPages && (
        <>
          {visiblePages[visiblePages.length - 1] < totalPages - 1 && (
            <BSPagination.Ellipsis disabled />
          )}
          <BSPagination.Item
            onClick={() => handlePageClick(totalPages)}
            active={currentPage === totalPages}
          >
            {totalPages}
          </BSPagination.Item>
        </>
      )}
      
      {/* Кнопка "Следующая" */}
      <BSPagination.Next
        onClick={() => handlePageClick(currentPage + 1)}
        disabled={currentPage === totalPages}
      />
    </BSPagination>
  );
});

Pagination.displayName = 'Pagination';

Pagination.propTypes = {
  currentPage: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
  maxVisiblePages: PropTypes.number,
  className: PropTypes.string
};

export default Pagination; 