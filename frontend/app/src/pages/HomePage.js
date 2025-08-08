import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import '../styles/HomePage.css';
import { API_URLS } from '../utils/constants';
import SimpleAddToCartButton from '../components/cart/SimpleAddToCartButton';
import CartUpdater from '../components/cart/CartUpdater';
import ProductRating from '../components/reviews/ProductRating';
import { useReviews } from '../context/ReviewContext';
import { Badge } from 'react-bootstrap';
import FavoriteButton from '../components/atoms/FavoriteButton';
import { useFavorites } from '../context/FavoritesContext';

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
  const { isFavorite, addFavorite, removeFavorite, loading: favLoading } = useFavorites();

  // Функция для форматирования URL изображения
  const formatImageUrl = (imageUrl) => {
    if (!imageUrl) return null;
    
    // Если URL начинается с http, значит он уже полный
    if (imageUrl.startsWith('http')) {
      return imageUrl;
    }
    
    // Если URL начинается с /, то добавляем базовый URL продуктового сервиса
    if (imageUrl.startsWith('/')) {
      return `${API_URLS.PRODUCT}${imageUrl}`;
    }
    
    // В противном случае просто возвращаем URL как есть
    return imageUrl;
  };

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
        const { items, total, limit } = response.data;
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

  // Компонент пагинации
  const Pagination = () => {
    if (pagination.totalPages <= 1) return null;
    
    return (
      <nav aria-label="Пагинация товаров">
        <ul className="pagination justify-content-center">
          <li className={`page-item ${pagination.currentPage === 1 ? 'disabled' : ''}`}>
            <button 
              className="page-link" 
              onClick={() => handlePageChange(pagination.currentPage - 1)}
              disabled={pagination.currentPage === 1}
            >
              &laquo; Назад
            </button>
          </li>
          
          {/* Генерируем страницы для отображения */}
          {Array.from({ length: pagination.totalPages }, (_, i) => i + 1)
            .filter(page => 
              // Показываем первую, последнюю и страницы рядом с текущей
              page === 1 || 
              page === pagination.totalPages || 
              Math.abs(page - pagination.currentPage) <= 2
            )
            .map((page, index, array) => {
              // Добавляем многоточие перед первой страницей, если она не 1 или 2
              const prevPage = index > 0 ? array[index - 1] : null;
              const showEllipsisBefore = prevPage !== null && page - prevPage > 1;
              
              return (
                <React.Fragment key={page}>
                  {showEllipsisBefore && (
                    <li className="page-item disabled">
                      <span className="page-link">...</span>
                    </li>
                  )}
                  <li className={`page-item ${pagination.currentPage === page ? 'active' : ''}`}>
                    <button 
                      className="page-link" 
                      onClick={() => handlePageChange(page)}
                    >
                      {page}
                    </button>
                  </li>
                </React.Fragment>
              );
            })}
          
          <li className={`page-item ${pagination.currentPage === pagination.totalPages ? 'disabled' : ''}`}>
            <button 
              className="page-link" 
              onClick={() => handlePageChange(pagination.currentPage + 1)}
              disabled={pagination.currentPage === pagination.totalPages}
            >
              Вперед &raquo;
            </button>
          </li>
        </ul>
      </nav>
    );
  };

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
        <div className="product-header">
          <h2>Наши продукты</h2>
          <div className="d-flex">
            <div className="me-3">
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
            {checkAdminRights() && (
              <Link to="/admin/products" className="btn btn-primary">
                <i className="bi bi-gear-fill me-1"></i>
                Управление товарами
              </Link>
            )}
          </div>
        </div>
        
        <CartUpdater />
        
        {products.length === 0 ? (
          <div className="no-products">
            <p>Продукты не найдены</p>
          </div>
        ) : (
          <>
            <div className="product-cards row g-4">
              {displayProducts.map(product => (
                <div key={product.id} className="col-md-3">
                  <div className="product-card position-relative">
                    <div className="position-absolute top-0 end-0 p-2 z-2">
                      <FavoriteButton
                        productId={product.id}
                        disabled={favLoading}
                      />
                    </div>
                    <Link to={`/products/${product.id}`} className="product-image-container">
                      {!product.image ? (
                        <div className="no-image-placeholder">
                          <i className="bi bi-image text-muted"></i>
                          <span>Нет изображения</span>
                        </div>
                      ) : (
                        <img 
                          src={formatImageUrl(product.image)}
                          alt={product.name}
                          className="product-image"
                        />
                      )}
                    </Link>
                    <div className="product-details">
                      <Link to={`/products/${product.id}`} className="product-title-link">
                        <h3>{product.name}</h3>
                      </Link>
                      <ProductRating productId={product.id} size="sm" />
                      <p className="price">{product.price} руб.</p>
                      <p className="description">{product.description}</p>
                      <div className="stock-status mb-2">
                        {product.stock > 0 ? (
                          <Badge bg="success" pill>В наличии ({product.stock} шт.)</Badge>
                        ) : (
                          <Badge bg="secondary" pill>Нет в наличии</Badge>
                        )}
                      </div>
                      <SimpleAddToCartButton 
                        productId={product.id}
                        stock={product.stock}
                        className="w-100"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Отображаем пагинацию */}
            <Pagination />
            
            {/* Отображаем информацию о пагинации */}
            <div className="pagination-info text-center mt-3">
              <p>
                Показано {products.length} из {pagination.totalItems} товаров 
                (Страница {pagination.currentPage} из {pagination.totalPages})
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default HomePage; 