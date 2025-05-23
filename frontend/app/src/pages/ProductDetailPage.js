import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { productAPI } from '../utils/api';
import { API_URLS } from '../utils/constants';
import AddToCartButton from '../components/cart/AddToCartButton';
import CartUpdater from '../components/cart/CartUpdater';
import '../styles/ProductDetailPage.css';
import ReviewList from '../components/reviews/ReviewList';
import ReviewForm from '../components/reviews/ReviewForm';
import ReviewStats from '../components/reviews/ReviewStats';
import { useAuth } from '../context/AuthContext';
import { useReviews } from '../context/ReviewContext';
import FavoriteButton from '../components/atoms/FavoriteButton';
import { useFavorites } from '../context/FavoritesContext';

const ProductDetailPage = () => {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [relatedProducts, setRelatedProducts] = useState([]);
  const [reviewPage, setReviewPage] = useState(1);
  const [reviewReloadKey, setReviewReloadKey] = useState(0);
  const { user } = useAuth();
  const { fetchBatchProductRatings } = useReviews();
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

  useEffect(() => {
    window.scrollTo(0, 0); // Прокручиваем страницу вверх при загрузке
    const fetchProductDetails = async () => {
      try {
        setLoading(true);
        
        // Проверяем флаг обновления кеша
        const refreshCache = localStorage.getItem('refreshProductsCache');
        let timestamp = '';
        
        if (refreshCache === 'true') {
          console.log('Обнаружен флаг обновления кеша продуктов, добавляем timestamp к запросу');
          timestamp = `?_t=${new Date().getTime()}`;
          localStorage.removeItem('refreshProductsCache');
        }
        
        // Получаем информацию о товаре (теперь с полной информацией о связанных сущностях)
        const response = await productAPI.getProductById(productId, timestamp);
        
        // Проверяем, есть ли данные в ответе
        if (!response.data) {
          setError('Товар не найден');
          setLoading(false);
          return;
        }
        
        // Товар уже содержит все связанные данные
        setProduct(response.data);
        
        // Получаем похожие товары
        try {
          // Используем категорию и подкатегорию товара для поиска похожих
          console.log('Запрашиваем похожие товары с параметрами:', {
            productId,
            categoryId: response.data.category_id,
            subcategoryId: response.data.subcategory_id
          });
          
          const relatedProducts = await productAPI.getRelatedProducts(
            productId, 
            response.data.category_id,
            response.data.subcategory_id
          );
          
          console.log('Получены похожие товары:', relatedProducts);
          console.log('Тип полученных данных:', typeof relatedProducts);
          console.log('Это массив?', Array.isArray(relatedProducts));
          console.log('Длина массива:', relatedProducts?.length);
          
          // Теперь relatedProducts - это массив товаров, а не объект с полем data
          if (relatedProducts && Array.isArray(relatedProducts)) {
            console.log('Устанавливаем похожие товары в состояние');
            setRelatedProducts(relatedProducts);
          } else {
            console.warn('Полученные похожие товары не являются массивом');
            setRelatedProducts([]);
          }
        } catch (relatedError) {
          console.error('Ошибка при загрузке похожих товаров:', relatedError);
          // Не устанавливаем ошибку, так как это не критично
          setRelatedProducts([]);
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Ошибка при загрузке товара:', err);
        setError('Не удалось загрузить информацию о товаре. Пожалуйста, попробуйте позже.');
        setLoading(false);
      }
    };
    
    fetchProductDetails();
  }, [productId]); // Перезагружаем при изменении ID товара

  // Подгружаем рейтинги только для похожих товаров через контекст
  useEffect(() => {
    if (relatedProducts && relatedProducts.length > 0) {
      // Извлекаем ID похожих товаров
      const relatedProductIds = relatedProducts.map(product => product.id);
      // Загружаем рейтинги пакетно только для похожих товаров
      fetchBatchProductRatings(relatedProductIds);
    }
  }, [relatedProducts, fetchBatchProductRatings]);

  const handleToggleFavorite = async () => {
    if (isFavorite(product.id)) await removeFavorite(product.id);
    else await addFavorite(product.id);
  };

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
      <CartUpdater />
      
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
              src={formatImageUrl(product.image)} 
              alt={product.name} 
            />
          ) : (
            <div className="no-image">Нет изображения</div>
          )}
        </div>

        <div className="product-detail-info">
          <h1 className="product-detail-title flex items-center gap-2">
            {product.name}
            <FavoriteButton
              productId={product.id}
              disabled={favLoading}
            />
          </h1>
          
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
            <AddToCartButton 
              productId={product.id}
              stock={product.stock}
              className="w-100"
            />
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
                      src={formatImageUrl(relatedProduct.image)} 
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

      {/* Секция отзывов */}
      <div className="product-reviews mt-5">
        {/* Статистика отзывов */}
        <ReviewStats productId={productId} key={`stats-${reviewReloadKey}`} />
        
        {/* Форма оставления отзыва (для авторизованных пользователей) */}
        {user && (
          <ReviewForm 
            productId={productId} 
            productName={product?.name} 
            onReviewSubmitted={() => setReviewReloadKey(prev => prev + 1)}
          />
        )}
        
        {/* Список отзывов */}
        <ReviewList 
          key={`review-list-${reviewReloadKey}`}
          productId={productId}
          page={reviewPage}
          onPageChange={setReviewPage}
        />
      </div>
    </div>
  );
};

export default ProductDetailPage;