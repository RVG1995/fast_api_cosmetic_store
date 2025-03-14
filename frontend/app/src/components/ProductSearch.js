import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { productAPI } from '../utils/api';
import '../styles/ProductSearch.css';

const ProductSearch = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchContainerRef = useRef(null);
  const debounceTimeoutRef = useRef(null);

  // Обработчик изменения поискового запроса
  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    // Очищаем предыдущий timeout
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    
    // Если поле пустое, скрываем результаты
    if (!value.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }
    
    // Устанавливаем новый timeout для debounce эффекта
    debounceTimeoutRef.current = setTimeout(() => {
      fetchSearchResults(value);
    }, 300); // Задержка в 300 мс
  };

  // Функция для получения результатов поиска
  const fetchSearchResults = async (term) => {
    if (!term.trim()) return;
    
    setIsLoading(true);
    try {
      const response = await productAPI.searchProducts(term);
      setSearchResults(response.data);
      setShowResults(true);
    } catch (error) {
      console.error('Ошибка при поиске товаров:', error);
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Обработчик клика вне компонента для скрытия результатов
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // Очистка таймера при размонтировании компонента
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  // Очистка поля поиска
  const handleClearSearch = () => {
    setSearchTerm('');
    setSearchResults([]);
    setShowResults(false);
  };

  return (
    <div className="product-search-container" ref={searchContainerRef}>
      <div className="search-input-container">
        <input
          type="text"
          className="form-control search-input"
          placeholder="Поиск товаров..."
          value={searchTerm}
          onChange={handleSearchChange}
          onFocus={() => searchResults.length > 0 && setShowResults(true)}
        />
        {searchTerm && (
          <button className="clear-search-btn" onClick={handleClearSearch}>
            <i className="bi bi-x-circle"></i>
          </button>
        )}
        {isLoading && (
          <div className="search-spinner">
            <div className="spinner-border spinner-border-sm" role="status">
              <span className="visually-hidden">Загрузка...</span>
            </div>
          </div>
        )}
      </div>
      
      {showResults && searchResults.length > 0 && (
        <div className="search-results-dropdown">
          {searchResults.map(product => (
            <Link 
              key={product.id} 
              to={`/products/${product.id}`} 
              className="search-result-item"
              onClick={() => setShowResults(false)}
            >
              <div className="search-result-image">
                {product.image ? (
                  <img 
                    src={`http://localhost:8001${product.image}`} 
                    alt={product.name} 
                  />
                ) : (
                  <div className="no-image">
                    <i className="bi bi-image"></i>
                  </div>
                )}
              </div>
              <div className="search-result-info">
                <div className="search-result-name">{product.name}</div>
                <div className="search-result-price">{product.price} ₽</div>
              </div>
            </Link>
          ))}
        </div>
      )}
      
      {showResults && searchTerm && searchResults.length === 0 && !isLoading && (
        <div className="search-results-dropdown">
          <div className="no-results">
            <i className="bi bi-search me-2"></i>
            Товары не найдены
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductSearch; 