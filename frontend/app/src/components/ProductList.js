import React, { useState, useEffect } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Button, Row, Col, Card } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { AddToCartButton } from './AddToCartButton';

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, isAdmin } = useAuth();
  const [sortOption, setSortOption] = useState('newest');

  useEffect(() => {
    const fetchProducts = async () => {
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
    };

    fetchProducts();
  }, [sortOption]);

  const handleSortChange = (e) => {
    setSortOption(e.target.value);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Вы уверены, что хотите удалить этот продукт?')) {
      try {
        await productAPI.deleteProduct(id);
        setProducts(products.filter(product => product.id !== id));
      } catch (err) {
        console.error('Ошибка при удалении продукта:', err);
        setError('Не удалось удалить продукт. Проверьте права доступа.');
      }
    }
  };

  if (loading) {
    return <div className="loading">Загрузка продуктов...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
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
        <Button
          variant="success"
          size="sm"
          className="mb-3 d-flex align-items-center"
          onClick={handleOpenCreateModal}
        >
          <i className="bi bi-plus-circle me-1"></i>
          Добавить товар
        </Button>
      )}
      
      {products.length === 0 ? (
        <p>Продукты не найдены</p>
      ) : (
        <div className="products-grid">
          {products.map(product => (
            <div key={product.id} className="product-card">
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
              </div>
              
              {isAdmin && (
                <div className="admin-actions">
                  <button className="btn btn-edit">Редактировать</button>
                  <button 
                    className="btn btn-delete"
                    onClick={() => handleDelete(product.id)}
                  >
                    Удалить
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProductList; 