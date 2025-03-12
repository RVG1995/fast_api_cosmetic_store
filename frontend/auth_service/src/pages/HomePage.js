import React, { useState, useEffect } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import '../styles/HomePage.css';

const HomePage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();
  
  // Изменяем размер страницы с 10 на 8
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    pageSize: 8
  });

  // Функция для загрузки товаров с учетом пагинации
  const fetchProducts = async (page = 1) => {
    try {
      setLoading(true);
      const response = await productAPI.getProducts(page, pagination.pageSize);
      console.log('API ответ продуктов:', response);
      
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
  }, []);

  // Обработчик изменения страницы
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      fetchProducts(newPage);
    }
  };

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

  // Безопасная проверка админских прав
  const hasAdminRights = () => {
    try {
      return isAdmin && isAdmin();
    } catch (error) {
      console.error('Ошибка при проверке прав администратора:', error);
      return false;
    }
  };

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
          {hasAdminRights() && (
            <Link to="/admin/products" className="btn btn-primary">
              <i className="bi bi-gear-fill me-1"></i>
              Управление товарами
            </Link>
          )}
        </div>
        
        {products.length === 0 ? (
          <div className="no-products">
            <p>Продукты не найдены</p>
          </div>
        ) : (
          <>
            <div className="product-cards row g-4">
              {products.map(product => (
                <div key={product.id} className="col-md-3">
                  <div className="product-card">
                    <div className="product-image">
                      {product.image ? (
                        <img src={`http://localhost:8001${product.image}`} alt={product.name} />
                      ) : (
                        <div className="no-image">Нет изображения</div>
                      )}
                    </div>
                    <div className="product-details">
                      <h3>{product.name}</h3>
                      <p className="price">{product.price} руб.</p>
                      <p className="description">{product.description}</p>
                      <p className="stock">
                        {product.stock > 0 ? `В наличии: ${product.stock}` : 'Нет в наличии'}
                      </p>
                      <button className="btn btn-primary">
                        <i className="bi bi-cart-plus me-1"></i>
                        В корзину
                      </button>
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