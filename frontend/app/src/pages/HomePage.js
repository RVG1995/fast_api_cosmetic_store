import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import '../styles/HomePage.css';
import CartUpdater from '../components/cart/CartUpdater';
import { useReviews } from '../context/ReviewContext';
import { useFavorites } from '../context/FavoritesContext';
import ProductCard from '../components/product/ProductCard';
import ListLayout from '../components/common/ListLayout';

const HomePage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();
  
  // Добавляем состояние для сортировки
  const [sortOption, setSortOption] = useState('newest');
  
  // Изменяем размер страницы с 10 на 8
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    pageSize: 8
  });

  const { fetchBatchProductRatings, productRatings } = useReviews();
  const { isFavorite, addFavorite, removeFavorite } = useFavorites();

  // Тоггл избранного
  const handleToggleFavorite = useCallback(async (productId) => {
    if (isFavorite(productId)) await removeFavorite(productId);
    else await addFavorite(productId);
  }, [isFavorite, addFavorite, removeFavorite]);

  // Функция для загрузки товаров с учетом пагинации и сортировки
  const fetchProducts = async (page = 1) => {
    try {
      setLoading(true);
      
      // Определяем тип сортировки
      const isRatingSort = sortOption === 'rating_desc' || sortOption === 'rating_asc';
      
      // Для сортировки по рейтингу запрашиваем все товары с базовой сортировкой
      if (isRatingSort) {
        const response = await productAPI.getProducts(1, 50, {}, 'newest'); // большой лимит для всех товаров
        console.log('API ответ продуктов (с сортировкой по рейтингу):', response);
        
        // Обновляем товары и информацию о пагинации
        const { items, total } = response.data;
        setProducts(Array.isArray(items) ? items : []);
        
        // Обновляем информацию о пагинации
        setPagination({
          currentPage: page,
          totalPages: Math.ceil(total / pagination.pageSize),
          totalItems: total,
          pageSize: pagination.pageSize
        });
      } else {
        // Обычная сортировка с сервера (newest, price_asc, price_desc)
        const response = await productAPI.getProducts(page, pagination.pageSize, {}, sortOption);
        console.log('API ответ продуктов (обычная сортировка):', response);
        
        // Обновляем товары и информацию о пагинации
        const { items, total, limit } = response.data;
        setProducts(Array.isArray(items) ? items : []);
        
        // Обновляем информацию о пагинации
        setPagination({
          currentPage: page,
          totalPages: Math.ceil(total / limit),
          totalItems: total,
          pageSize: limit
        });
      }
      
      setError(null);
    } catch (err) {
      console.error('Ошибка при загрузке продуктов:', err);
      setError('Не удалось загрузить продукты. Пожалуйста, попробуйте позже.');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  // Загрузка товаров при первой загрузке
  useEffect(() => {
    fetchProducts(1);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortOption]);

  // Обработчик изменения страницы
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      fetchProducts(newPage);
    }
  };

  // Обработчик изменения сортировки
  const handleSortChange = (e) => {
    setSortOption(e.target.value);
    // fetchProducts будет вызван через useEffect
  };

  // Client-side сортировка по рейтингу
  const displayProducts = useMemo(() => {
    // Для сортировки по рейтингу
    if (sortOption === 'rating_desc' || sortOption === 'rating_asc') {
      // Копируем массив для сортировки
      const sortedItems = [...products];
      
      // Сортируем по рейтингу
      if (sortOption === 'rating_desc') {
        sortedItems.sort((a, b) =>
          (productRatings[b.id]?.average_rating || 0) -
          (productRatings[a.id]?.average_rating || 0)
        );
      } else { // rating_asc
        sortedItems.sort((a, b) =>
          (productRatings[a.id]?.average_rating || 0) -
          (productRatings[b.id]?.average_rating || 0)
        );
      }
      
      // Применяем пагинацию на клиенте
      const startIndex = (pagination.currentPage - 1) * pagination.pageSize;
      const endIndex = startIndex + pagination.pageSize;
      return sortedItems.slice(startIndex, endIndex);
    }
    
    // Для не-рейтинговых сортировок возвращаем как есть (пагинация с сервера)
    return products;
  }, [products, sortOption, productRatings, pagination.currentPage, pagination.pageSize]);

  // Пагинация вынесена в общий компонент

  // Вспомогательная функция для проверки прав администратора
  const checkAdminRights = () => {
    return isAdmin;
  };

  // После загрузки товаров, загружаем их рейтинги
  useEffect(() => {
    const allProducts = [...products];
    if (allProducts.length > 0) {
      // Извлекаем уникальные ID товаров
      const productIds = [...new Set(allProducts.map(product => product.id))];
      // Загружаем рейтинги пакетно
      fetchBatchProductRatings(productIds);
    }
  }, [products, fetchBatchProductRatings]);

  if (loading) {
    return (
      <div className="container">
        <div className="loading-spinner">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
          <p>Загрузка продуктов...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      <div className="container" style={{ maxWidth: '1200px' }}>
        <ListLayout
          title="Наши продукты"
          headerExtras={checkAdminRights() && (
            <Link to="/admin/products" className="btn btn-primary">
              <i className="bi bi-gear-fill me-1"></i>
              Управление товарами
            </Link>
          )}
          summary={(
            <div className="d-flex align-items-center">
              <select 
                className="form-select" 
                value={sortOption} 
                onChange={handleSortChange}
                aria-label="Сортировка товаров"
              >
                <option value="newest">Новые сначала</option>
                <option value="price_asc">Цена (по возрастанию)</option>
                <option value="price_desc">Цена (по убыванию)</option>
                <option value="rating_asc">Рейтинг (по возрастанию)</option>
                <option value="rating_desc">Рейтинг (по убыванию)</option>
              </select>
            </div>
          )}
          loading={loading}
          error={error}
          empty={products.length === 0}
          emptyNode={<div className="no-products"><p>Продукты не найдены</p></div>}
          currentPage={pagination.currentPage}
          totalPages={pagination.totalPages}
          onPageChange={handlePageChange}
          footer={(
            <div className="pagination-info text-center mt-3">
              <p>
                Показано {products.length} из {pagination.totalItems} товаров 
                (Страница {pagination.currentPage} из {pagination.totalPages})
              </p>
            </div>
          )}
        >
        
        <CartUpdater />
        
            <div className="product-cards row g-4">
              {displayProducts.map(product => (
                <div key={product.id} className="col-md-3">
                  <ProductCard 
                    product={product}
                    isFavorite={isFavorite(product.id)}
                    onToggleFavorite={() => handleToggleFavorite(product.id)}
                  />
                </div>
              ))}
            </div>
            
        </ListLayout>
      </div>
    </div>
  );
};

export default HomePage; 