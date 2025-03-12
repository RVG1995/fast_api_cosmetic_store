import React from 'react';
import ProductList from '../components/ProductList';
import { useAuth } from '../context/AuthContext';

const ProductsPage = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading">Загрузка...</div>;
  }

  return (
    <div className="products-page">
      <div className="page-header">
        <h1>Каталог продуктов</h1>
        {user && (
          <p>Добро пожаловать, {user.first_name} {user.last_name}!</p>
        )}
      </div>
      
      <ProductList />
    </div>
  );
};

export default ProductsPage; 