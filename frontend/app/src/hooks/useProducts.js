import { useState, useEffect, useCallback, useMemo } from 'react';
import { productAPI } from '../utils/api';

export const useProducts = (initialPage = 1, initialPageSize = 10, initialFilters = {}, initialSort = 'newest') => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const [sortOption, setSortOption] = useState(initialSort);
  const [pagination, setPagination] = useState({
    currentPage: initialPage,
    totalPages: 1,
    totalItems: 0,
    pageSize: initialPageSize
  });

  // Функция для загрузки товаров с учетом пагинации, фильтров и сортировки
  const fetchProducts = useCallback(async (
    page = pagination.currentPage, 
    pageSize = pagination.pageSize, 
    currentFilters = filters,
    sort = sortOption
  ) => {
    try {
      setLoading(true);
      setError(null);
      
      // Получаем только активные фильтры (не пустые)
      const activeFilters = {};
      Object.keys(currentFilters).forEach(key => {
        if (currentFilters[key]) {
          activeFilters[key] = currentFilters[key];
        }
      });
      
      console.log('Вызов API getProducts с параметрами:', { page, pageSize, activeFilters, sort });
      
      const response = await productAPI.getProducts(page, pageSize, activeFilters, sort);
      
      if (response && response.data) {
        const { items, total, limit } = response.data;
        
        setProducts(Array.isArray(items) ? items : []);
        
        setPagination({
          currentPage: page,
          totalPages: Math.ceil(total / limit),
          totalItems: total,
          pageSize: limit
        });
      } else {
        setError('Получен некорректный ответ от сервера');
      }
    } catch (err) {
      console.error('Ошибка при загрузке продуктов:', err);
      setError(err.message || 'Не удалось загрузить продукты. Пожалуйста, попробуйте позже.');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.currentPage, pagination.pageSize, sortOption]);

  // Загружаем товары при изменении фильтров или сортировки
  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Функция для обновления фильтров
  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => {
      const updated = { ...prev, ...newFilters };
      return updated;
    });
    // При изменении фильтров возвращаемся к первой странице
    setPagination(prev => ({ ...prev, currentPage: 1 }));
  }, []);

  // Функция для обновления сортировки
  const updateSort = useCallback((newSort) => {
    setSortOption(newSort);
  }, []);

  // Функция для перехода на указанную страницу
  const goToPage = useCallback((page) => {
    if (page >= 1 && page <= pagination.totalPages) {
      setPagination(prev => ({ ...prev, currentPage: page }));
    }
  }, [pagination.totalPages]);

  // Получение отфильтрованных продуктов с мемоизацией
  const filteredProducts = useMemo(() => {
    return products;
  }, [products]);

  return {
    products: filteredProducts,
    loading,
    error,
    pagination,
    filters,
    sortOption,
    updateFilters,
    updateSort,
    goToPage,
    refetch: fetchProducts
  };
};

export default useProducts; 