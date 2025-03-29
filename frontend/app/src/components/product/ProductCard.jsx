import React, { memo, useState, useEffect } from 'react';
import { Card, Badge } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import ProgressiveImage from '../common/ProgressiveImage';
import SimpleAddToCartButton from '../cart/SimpleAddToCartButton';
import ProductRating from '../reviews/ProductRating';
import { API_URLS } from '../../utils/constants';
import './ProductCard.css';

/**
 * Компонент для отображения карточки товара в списке товаров
 */
const ProductCard = memo(({ product }) => {
  const [imageUrl, setImageUrl] = useState(null);
  const [imageError, setImageError] = useState(false);
  
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
  
  // Устанавливаем URL изображения при изменении продукта
  useEffect(() => {
    if (product && product.image) {
      const formattedUrl = formatImageUrl(product.image);
      console.log('ProductCard: форматированный URL изображения:', formattedUrl);
      setImageUrl(formattedUrl);
      setImageError(false);
    } else {
      console.warn('ProductCard: отсутствует изображение для продукта:', product?.id);
      setImageUrl(null);
      setImageError(true);
    }
  }, [product]);
  
  return (
    <Card className="product-card h-100">
      <Link to={`/products/${product.id}`} className="product-image-container">
        {!imageError && imageUrl ? (
          <ProgressiveImage 
            src={imageUrl}
            alt={product.name}
            className="product-image"
            placeholderClassName="product-image-placeholder"
          />
        ) : (
          <div className="no-image-placeholder">
            <i className="bi bi-image text-muted"></i>
            <span>Нет изображения</span>
          </div>
        )}
        
        {/* Бейджи для акций/скидок */}
        {product.discount_percent > 0 && (
          <Badge bg="danger" className="discount-badge">
            -{product.discount_percent}%
          </Badge>
        )}
        
        {product.is_new && (
          <Badge bg="success" className="new-badge">
            Новинка
          </Badge>
        )}
      </Link>
      
      <Card.Body className="d-flex flex-column">
        <div className="brand-category mb-1">
          {product.brand_name && (
            <small className="text-muted brand-name">{product.brand_name}</small>
          )}
        </div>
        
        <Link to={`/products/${product.id}`} className="product-title-link">
          <Card.Title className="product-title">
            {product.name}
          </Card.Title>
        </Link>
        
        <ProductRating productId={product.id} size="sm" className="mb-2" />
        
        <Card.Text className="product-description text-truncate-3">
          {product.description}
        </Card.Text>
        
        <div className="mt-auto">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <div className="price-block">
              {product.discount_percent > 0 ? (
                <>
                  <span className="original-price text-muted">
                    {product.original_price} руб.
                  </span>
                  <span className="current-price">
                    {product.price} руб.
                  </span>
                </>
              ) : (
                <span className="current-price">
                  {product.price} руб.
                </span>
              )}
            </div>
            
            <div className="stock-status">
              {product.stock > 0 ? (
                <Badge bg="success" pill>В наличии</Badge>
              ) : (
                <Badge bg="secondary" pill>Нет в наличии</Badge>
              )}
            </div>
          </div>
          
          <SimpleAddToCartButton 
            productId={product.id}
            stock={product.stock}
            className="w-100"
          />
        </div>
      </Card.Body>
    </Card>
  );
});

ProductCard.displayName = 'ProductCard';

ProductCard.propTypes = {
  product: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    price: PropTypes.number.isRequired,
    original_price: PropTypes.number,
    stock: PropTypes.number.isRequired,
    image: PropTypes.string,
    discount_percent: PropTypes.number,
    is_new: PropTypes.bool,
    brand_name: PropTypes.string
  }).isRequired
};

export default ProductCard; 