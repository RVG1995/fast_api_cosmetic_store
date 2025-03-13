import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { productAPI } from '../utils/api';
import '../styles/ProductDetailPage.css';

const ProductDetailPage = () => {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [relatedProducts, setRelatedProducts] = useState([]);

  useEffect(() => {
    const fetchProductDetails = async () => {
      try {
        setLoading(true);
        // Получаем информацию о товаре
        const response = await productAPI.getProductById(productId);
        
        // Проверяем, есть ли данные в ответе
        if (!response.data) {
          setError('Товар не найден');
          setLoading(false);
          return;
        }
        
        const productData = response.data;
        
        // Загружаем дополнительные данные
        let enhancedProduct = { ...productData };
        
        try {
          // Загружаем категорию
          if (productData.category_id) {
            const categoryResponse = await productAPI.getCategoryById(productData.category_id);
            enhancedProduct.category = categoryResponse.data;
          }
          
          // Загружаем подкатегорию
          if (productData.subcategory_id) {
            const subcategoryResponse = await productAPI.getSubcategoryById(productData.subcategory_id);
            enhancedProduct.subcategory = subcategoryResponse.data;
          }
          
          // Загружаем бренд
          if (productData.brand_id) {
            const brandResponse = await productAPI.getBrandById(productData.brand_id);
            enhancedProduct.brand = brandResponse.data;
          }
          
          // Загружаем страну
          if (productData.country_id) {
            const countryResponse = await productAPI.getCountryById(productData.country_id);
            enhancedProduct.country = countryResponse.data;
          }
        } catch (err) {
          console.error('Ошибка при загрузке дополнительных данных о товаре:', err);
          // Не прерываем выполнение даже если не удалось загрузить дополнительные данные
        }
        
        // Сохраняем обогащенные данные о товаре
        setProduct(enhancedProduct);
        
        // После получения информации о товаре, загружаем похожие товары
        if (productData.category_id) {
          const relatedResponse = await productAPI.getProducts(1, 4, {
            category_id: productData.category_id,
          });
          // Фильтруем, чтобы исключить текущий товар из списка похожих
          const filtered = relatedResponse.data.items.filter(item => item.id !== parseInt(productId));
          setRelatedProducts(filtered);
        }
      } catch (err) {
        console.error('Ошибка при загрузке данных о товаре:', err);
        
        // Определяем тип ошибки
        if (err.response && err.response.status === 404) {
          setError('Товар не найден');
        } else {
          setError('Не удалось загрузить информацию о товаре');
        }
      } finally {
        setLoading(false);
      }
    };

    if (productId) {
      fetchProductDetails();
    }
  }, [productId]);

  if (loading) {
    return (
      <div className="product-detail-container loading">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="product-detail-container error">
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Ошибка</h4>
          <p>{error}</p>
          <p>Возможно, товар был удален или перемещен.</p>
        </div>
        <Link to="/products" className="btn btn-primary mt-3">
          Вернуться к списку товаров
        </Link>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="product-detail-container not-found">
        <div className="alert alert-warning" role="alert">
          <h4 className="alert-heading">Товар не найден</h4>
          <p>Запрашиваемый товар не существует или был удален.</p>
        </div>
        <Link to="/products" className="btn btn-primary mt-3">
          Вернуться к списку товаров
        </Link>
      </div>
    );
  }

  return (
    <div className="product-detail-container">
      <div className="product-detail-breadcrumb">
        <Link to="/">Главная</Link> &gt; 
        <Link to="/products">Товары</Link> &gt; 
        {product.category && (
          <>
            <Link to={`/products?category_id=${product.category_id}`}>
              {product.category.name}
            </Link> &gt; 
          </>
        )}
        <span>{product.name}</span>
      </div>

      <div className="product-detail-content">
        <div className="product-detail-image">
          {product.image ? (
            <img 
              src={`http://localhost:8001${product.image}`} 
              alt={product.name} 
            />
          ) : (
            <div className="no-image">Нет изображения</div>
          )}
        </div>

        <div className="product-detail-info">
          <h1 className="product-detail-title">{product.name}</h1>
          
          <div className="product-detail-price">
            <span className="price-value">{product.price} ₽</span>
            <span className={`stock-status ${product.stock > 0 ? 'in-stock' : 'out-of-stock'}`}>
              {product.stock > 0 ? `В наличии: ${product.stock} шт.` : 'Нет в наличии'}
            </span>
          </div>
          
          <div className="product-detail-categories">
            {product.category && (
              <div className="category-item">
                <span className="category-label">Категория:</span>
                <Link to={`/products?category_id=${product.category_id}`}>
                  {product.category.name}
                </Link>
              </div>
            )}
            
            {product.subcategory && (
              <div className="category-item">
                <span className="category-label">Подкатегория:</span>
                <Link to={`/products?subcategory_id=${product.subcategory_id}`}>
                  {product.subcategory.name}
                </Link>
              </div>
            )}
            
            {product.brand && (
              <div className="category-item">
                <span className="category-label">Бренд:</span>
                <Link to={`/products?brand_id=${product.brand_id}`}>
                  {product.brand.name}
                </Link>
              </div>
            )}
            
            {product.country && (
              <div className="category-item">
                <span className="category-label">Страна:</span>
                <Link to={`/products?country_id=${product.country_id}`}>
                  {product.country.name}
                </Link>
              </div>
            )}
          </div>
          
          <div className="product-detail-actions">
            <button 
              className="btn btn-primary btn-lg"
              disabled={product.stock <= 0}
            >
              Добавить в корзину
            </button>
          </div>
          
          <div className="product-detail-description">
            <h3>Описание</h3>
            <p>{product.description || 'Описание отсутствует'}</p>
          </div>
        </div>
      </div>

      {relatedProducts.length > 0 && (
        <div className="related-products">
          <h3>Похожие товары</h3>
          <div className="related-products-grid">
            {relatedProducts.map(relatedProduct => (
              <div key={relatedProduct.id} className="related-product-card">
                <Link to={`/products/${relatedProduct.id}`}>
                  {relatedProduct.image ? (
                    <img 
                      src={`http://localhost:8001${relatedProduct.image}`} 
                      alt={relatedProduct.name} 
                    />
                  ) : (
                    <div className="no-image">Нет фото</div>
                  )}
                  <div className="related-product-name">{relatedProduct.name}</div>
                  <div className="related-product-price">{relatedProduct.price} ₽</div>
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductDetailPage; 