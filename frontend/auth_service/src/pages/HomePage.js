import React, { useState, useEffect } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import '../styles/HomePage.css';

const HomePage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, isAdmin } = useAuth();

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const response = await productAPI.getProducts();
        console.log('API ответ продуктов:', response);
        // Защита от undefined с фолбэком на пустой массив
        setProducts(Array.isArray(response?.data) ? response.data : []);
        setError(null);
      } catch (err) {
        console.error('Ошибка при загрузке продуктов:', err);
        setError('Не удалось загрузить продукты. Пожалуйста, попробуйте позже.');
        setProducts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

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
        <div className="product-cards">
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
                <button className="btn btn-primary">
                  <i className="bi bi-cart-plus me-1"></i>
                  В корзину
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HomePage; 