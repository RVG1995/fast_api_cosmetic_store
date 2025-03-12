import React, { useState, useEffect } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, isAdmin } = useAuth();

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const response = await productAPI.getProducts();
        setProducts(response.data);
        setError(null);
      } catch (err) {
        console.error('Ошибка при загрузке продуктов:', err);
        setError('Не удалось загрузить продукты. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

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
      <h2>Список продуктов</h2>
      
      {isAdmin() && (
        <div className="admin-controls">
          <button className="btn btn-primary">Добавить новый продукт</button>
        </div>
      )}
      
      {products.length === 0 ? (
        <p>Продукты не найдены</p>
      ) : (
        <div className="products-grid">
          {products.map(product => (
            <div key={product.id} className="product-card">
              <div className="product-image">
                {product.image ? (
                  <img src={product.image} alt={product.name} />
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
              
              {isAdmin() && (
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