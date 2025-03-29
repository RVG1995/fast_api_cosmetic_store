import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Button, Row, Col, Card } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { AddToCartButton } from './AddToCartButton';
import ProgressiveImage from './common/ProgressiveImage';
import ErrorMessage from './common/ErrorMessage';
import { API_URLS } from '../utils/constants';

// Мемоизированный компонент карточки товара
const ProductCard = memo(({ product, isAdmin, onDelete }) => {
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

  return (
    <div className="product-card">
      <div className="product-image">
        {product.image ? (
          <ProgressiveImage 
            src={formatImageUrl(product.image)} 
            alt={product.name} 
            aspectRatio="1:1" 
          />
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
      </div>
      
      {isAdmin && (
        <div className="admin-actions">
          <Link to={`/admin/products/${product.id}`} className="btn btn-primary btn-sm me-2">
            <i className="bi bi-pencil me-1"></i>
            Редактировать
          </Link>
          <button 
            className="btn btn-danger btn-sm"
            onClick={() => onDelete(product.id)}
          >
            <i className="bi bi-trash me-1"></i>
            Удалить
          </button>
        </div>
      )}
    </div>
  );
});

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, isAdmin } = useAuth();
  const [sortOption, setSortOption] = useState('newest');

  // Мемоизированная функция загрузки продуктов
  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await productAPI.getProducts(1, 50, {}, sortOption !== 'newest' ? sortOption : null);
      setProducts(response.data.items || []);
      setError(null);
    } catch (err) {
      console.error('Ошибка при загрузке продуктов:', err);
      setError('Не удалось загрузить продукты. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  }, [sortOption]);

  // Вызов загрузки при монтировании и изменении сортировки
  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Мемоизированный обработчик изменения сортировки
  const handleSortChange = useCallback((e) => {
    setSortOption(e.target.value);
  }, []);

  // Мемоизированный обработчик удаления
  const handleDelete = useCallback(async (id) => {
    if (window.confirm('Вы уверены, что хотите удалить этот продукт?')) {
      try {
        await productAPI.deleteProduct(id);
        setProducts(prevProducts => prevProducts.filter(product => product.id !== id));
      } catch (err) {
        console.error('Ошибка при удалении продукта:', err);
        setError('Не удалось удалить продукт. Проверьте права доступа.');
      }
    }
  }, []);

  // Отрисовка загрузки
  if (loading && products.length === 0) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Загрузка продуктов...</span>
        </div>
      </div>
    );
  }

  // Отображение ошибки
  if (error) {
    return <ErrorMessage error={error} retry={fetchProducts} />;
  }

  return (
    <div className="product-list">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Список продуктов</h2>
        
        <div className="d-flex align-items-center">
          <label htmlFor="sortSelect" className="me-2">Сортировка:</label>
          <select 
            id="sortSelect" 
            className="form-select" 
            value={sortOption} 
            onChange={handleSortChange}
          >
            <option value="newest">Новые сначала</option>
            <option value="price_asc">Цена (по возрастанию)</option>
            <option value="price_desc">Цена (по убыванию)</option>
          </select>
        </div>
      </div>
      
      {/* Кнопка создания товара для администраторов */}
      {isAdmin && (
        <Link to="/admin/products/create" className="btn btn-success mb-3 d-flex align-items-center" style={{ width: 'fit-content' }}>
          <i className="bi bi-plus-circle me-1"></i>
          Добавить товар
        </Link>
      )}
      
      {loading && products.length > 0 && (
        <div className="alert alert-info" role="alert">
          <div className="spinner-border spinner-border-sm me-2" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
          Обновление списка продуктов...
        </div>
      )}
      
      {products.length === 0 ? (
        <div className="alert alert-warning" role="alert">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          Продукты не найдены
        </div>
      ) : (
        <div className="products-grid">
          {products.map(product => (
            <ProductCard 
              key={product.id} 
              product={product} 
              isAdmin={isAdmin} 
              onDelete={handleDelete} 
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default memo(ProductList); 