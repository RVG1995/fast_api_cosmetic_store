import React, { useState, useEffect } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import CartUpdater from '../components/cart/CartUpdater';
import { API_URLS } from '../utils/constants';
import '../styles/HomePage.css';

const ProductsPage = () => {
  const { search } = useLocation();
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(search);
  
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAdmin } = useAuth();
  
  // Состояние для фильтров
  const [filters, setFilters] = useState({
    category_id: queryParams.get('category_id') || '',
    subcategory_id: queryParams.get('subcategory_id') || '',
    brand_id: queryParams.get('brand_id') || '',
    country_id: queryParams.get('country_id') || '',
  });
  
  // Добавляем состояние для сортировки
  const [sortOption, setSortOption] = useState(queryParams.get('sort') || 'newest');
  
  // Состояние для данных, необходимых для фильтров
  const [categories, setCategories] = useState([]);
  const [subcategories, setSubcategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [countries, setCountries] = useState([]);
  
  // Состояние для отфильтрованных подкатегорий по выбранной категории
  const [filteredSubcategories, setFilteredSubcategories] = useState([]);
  
  // Изменяем размер страницы с 10 на 8
  const [pagination, setPagination] = useState({
    currentPage: parseInt(queryParams.get('page') || '1', 10),
    totalPages: 1,
    totalItems: 0,
    pageSize: 8
  });

  // Функция для загрузки данных для фильтров
  const fetchFilterData = async () => {
    try {
      const [categoriesRes, subcategoriesRes, brandsRes, countriesRes] = await Promise.all([
        productAPI.getCategories(),
        productAPI.getSubcategories(),
        productAPI.getBrands(),
        productAPI.getCountries()
      ]);
      
      setCategories(categoriesRes.data);
      setSubcategories(subcategoriesRes.data);
      setBrands(brandsRes.data);
      setCountries(countriesRes.data);
      
      // Если выбрана категория, обновляем отфильтрованные подкатегории
      if (filters.category_id) {
        setFilteredSubcategories(
          subcategoriesRes.data.filter(
            sub => sub.category_id === parseInt(filters.category_id, 10)
          )
        );
      }
    } catch (err) {
      console.error('Ошибка при загрузке данных для фильтров:', err);
      setError('Не удалось загрузить данные фильтров. Пожалуйста, попробуйте позже.');
    }
  };

  // Функция для загрузки товаров с учетом пагинации и фильтров
  const fetchProducts = async (page = 1, currentFilters = filters) => {
    try {
      setLoading(true);
      
      // Создаем объект с только непустыми фильтрами
      const activeFilters = {};
      Object.keys(currentFilters).forEach(key => {
        if (currentFilters[key]) {
          activeFilters[key] = currentFilters[key];
        }
      });
      
      // Более не добавляем sortOption в activeFilters, т.к. передадим напрямую
      // Это предотвратит двойное добавление параметра sort
      
      console.log('Вызываем API с параметрами:', { page, pageSize: pagination.pageSize, activeFilters, sortOption });
      // Передаем sortOption непосредственно четвертым параметром
      const response = await productAPI.getProducts(page, pagination.pageSize, activeFilters, sortOption);
      console.log('API ответ продуктов:', response);
      
      // Обновляем товары и информацию о пагинации
      const { items, total, limit } = response.data;
      console.log(`Получено ${items?.length} товаров из ${total} с лимитом ${limit}`);
      
      // Товары уже отсортированы на сервере, отключаем клиентскую сортировку
      let sortedItems = Array.isArray(items) ? [...items] : [];
      
      // Логируем полученные товары по цене для отладки
      if (sortedItems.length > 0) {
        console.log('Цены первых 5 товаров:', sortedItems.slice(0, 5).map(item => item.price));
        
        // Проверяем порядок сортировки
        if (sortOption === 'price_asc') {
          console.log('Должны быть отсортированы по возрастанию цены');
          const isSortedAsc = sortedItems.every((item, i) => 
            i === 0 || item.price >= sortedItems[i-1].price
          );
          console.log('Сортировка по возрастанию цены корректна:', isSortedAsc);
        } else if (sortOption === 'price_desc') {
          console.log('Должны быть отсортированы по убыванию цены');
          const isSortedDesc = sortedItems.every((item, i) => 
            i === 0 || item.price <= sortedItems[i-1].price
          );
          console.log('Сортировка по убыванию цены корректна:', isSortedDesc);
        }
      }
      
      setProducts(sortedItems);
      
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

  // Загрузка товаров и данных для фильтров при первой загрузке
  useEffect(() => {
    fetchFilterData();
    fetchProducts(pagination.currentPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Слушатель изменений URL
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const newFilters = {
      category_id: queryParams.get('category_id') || '',
      subcategory_id: queryParams.get('subcategory_id') || '',
      brand_id: queryParams.get('brand_id') || '',
      country_id: queryParams.get('country_id') || '',
    };
    
    // Получаем параметр сортировки из URL
    const newSortOption = queryParams.get('sort') || 'newest';
    
    // Обновляем состояние фильтров и сортировки
    setFilters(newFilters);
    setSortOption(newSortOption);
    
    // Устанавливаем новую страницу из URL или по умолчанию 1
    const page = parseInt(queryParams.get('page') || '1', 10);
    setPagination(prev => ({
      ...prev,
      currentPage: page
    }));
    
    // Загружаем товары с новыми фильтрами и сортировкой
    fetchProducts(page, newFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  // Обновляем URL при изменении фильтров, сортировки или страницы
  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.category_id) params.set('category_id', filters.category_id);
    if (filters.subcategory_id) params.set('subcategory_id', filters.subcategory_id);
    if (filters.brand_id) params.set('brand_id', filters.brand_id);
    if (filters.country_id) params.set('country_id', filters.country_id);
    if (sortOption !== 'newest') params.set('sort', sortOption);
    if (pagination.currentPage > 1) params.set('page', pagination.currentPage.toString());
    
    navigate({ search: params.toString() }, { replace: true });
  }, [filters, sortOption, pagination.currentPage, navigate]);

  // Обновляем фильтрованные подкатегории при изменении категории
  useEffect(() => {
    if (filters.category_id) {
      const catId = parseInt(filters.category_id, 10);
      setFilteredSubcategories(
        subcategories.filter(sub => sub.category_id === catId)
      );
      // Сбрасываем выбранную подкатегорию, если она не принадлежит текущей категории
      if (filters.subcategory_id) {
        const subCat = subcategories.find(sub => 
          sub.id === parseInt(filters.subcategory_id, 10)
        );
        if (!subCat || subCat.category_id !== catId) {
          setFilters(prev => ({ ...prev, subcategory_id: '' }));
        }
      }
    } else {
      setFilteredSubcategories([]);
      // Сбрасываем подкатегорию, если не выбрана категория
      if (filters.subcategory_id) {
        setFilters(prev => ({ ...prev, subcategory_id: '' }));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.category_id, subcategories]);

  // Обработчик изменения фильтров
  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    
    // Если изменилась категория, сбрасываем подкатегорию
    if (name === 'category_id' && value !== filters.category_id) {
      setFilters(prev => ({ ...prev, [name]: value, subcategory_id: '' }));
    } else {
      setFilters(prev => ({ ...prev, [name]: value }));
    }
    
    // При изменении фильтров сбрасываем на первую страницу
    setPagination(prev => ({ ...prev, currentPage: 1 }));
    
    // Загружаем продукты с новыми фильтрами
    const newFilters = { ...filters, [name]: value };
    if (name === 'category_id' && value !== filters.category_id) {
      newFilters.subcategory_id = '';
    }
    
    fetchProducts(1, newFilters);
  };
  
  // Добавляем обработчик изменения сортировки
  const handleSortChange = (e) => {
    const newSortOption = e.target.value;
    console.log(`Изменение сортировки с ${sortOption} на ${newSortOption}`);
    setSortOption(newSortOption);
    
    // При изменении сортировки сбрасываем на первую страницу
    setPagination(prev => ({ ...prev, currentPage: 1 }));
    
    // Создаем объект с только непустыми фильтрами
    const activeFilters = {};
    Object.keys(filters).forEach(key => {
      if (filters[key]) {
        activeFilters[key] = filters[key];
      }
    });
    
    // Добавляем параметр сортировки для дебага
    if (newSortOption !== 'newest') {
      console.log(`Добавляем сортировку ${newSortOption} в активные фильтры`);
      activeFilters.sort = newSortOption;
    }
    
    console.log('Активные фильтры перед запросом:', activeFilters);
    
    // Загружаем товары с новой сортировкой
    fetchProducts(1, filters);
  };

  // Обработчик сброса фильтров
  const handleResetFilters = () => {
    const emptyFilters = {
      category_id: '',
      subcategory_id: '',
      brand_id: '',
      country_id: '',
    };
    setFilters(emptyFilters);
    setSortOption('newest'); // Сбрасываем сортировку к значению по умолчанию
    setPagination(prev => ({ ...prev, currentPage: 1 }));
    
    // Очищаем URL от параметров
    navigate('', { replace: true });
    
    // Загружаем товары без фильтров
    fetchProducts(1, emptyFilters);
  };

  // Обработчик изменения страницы
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      setPagination(prev => ({ ...prev, currentPage: newPage }));
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

  // Отображение фильтров
  const FiltersPanel = () => {
    return (
      <div className="filters-panel card mb-4">
        <div className="card-header bg-primary text-white">
          <h5 className="mb-0">Фильтры товаров</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-3">
              <label htmlFor="category_id" className="form-label">Категория</label>
              <select 
                className="form-select" 
                id="category_id" 
                name="category_id"
                value={filters.category_id}
                onChange={handleFilterChange}
              >
                <option value="">Все категории</option>
                {categories.map(category => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="col-md-3">
              <label htmlFor="subcategory_id" className="form-label">Подкатегория</label>
              <select 
                className="form-select" 
                id="subcategory_id" 
                name="subcategory_id"
                value={filters.subcategory_id}
                onChange={handleFilterChange}
                disabled={!filters.category_id || filteredSubcategories.length === 0}
              >
                <option value="">Все подкатегории</option>
                {filteredSubcategories.map(subcategory => (
                  <option key={subcategory.id} value={subcategory.id}>
                    {subcategory.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="col-md-3">
              <label htmlFor="brand_id" className="form-label">Бренд</label>
              <select 
                className="form-select" 
                id="brand_id" 
                name="brand_id"
                value={filters.brand_id}
                onChange={handleFilterChange}
              >
                <option value="">Все бренды</option>
                {brands.map(brand => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="col-md-3">
              <label htmlFor="country_id" className="form-label">Страна</label>
              <select 
                className="form-select" 
                id="country_id" 
                name="country_id"
                value={filters.country_id}
                onChange={handleFilterChange}
              >
                <option value="">Все страны</option>
                {countries.map(country => (
                  <option key={country.id} value={country.id}>
                    {country.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Добавляем сортировку по цене в блок фильтров */}
          <div className="row mt-3">
            <div className="col-md-3">
              <label htmlFor="sort" className="form-label">Сортировка по цене</label>
              <select 
                className="form-select" 
                id="sort"
                value={sortOption}
                onChange={handleSortChange}
              >
                <option value="newest">По умолчанию</option>
                <option value="price_asc">Цена (по возрастанию)</option>
                <option value="price_desc">Цена (по убыванию)</option>
              </select>
            </div>
            <div className="col-md-9 d-flex align-items-end justify-content-end">
              <button 
                className="btn btn-secondary" 
                onClick={handleResetFilters}
              >
                Сбросить фильтры
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

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

  if (loading && products.length === 0) {
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

  return (
    <div className="container py-4">
      {/* Компонент для обновления данных корзины при загрузке страницы */}
      <CartUpdater />
      
      <div className="products-page-wrapper">
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h1 className="products-heading mb-0">Каталог товаров</h1>
          {hasAdminRights() && (
            <Link to="/admin/products" className="btn btn-primary">
              <i className="bi bi-gear-fill me-1"></i>
              Управление товарами
            </Link>
          )}
        </div>
        
        {/* Панель фильтров */}
        <FiltersPanel />
        
        {/* Показываем только информацию о товарах, убираем отдельную панель сортировки */}
        <div className="d-flex justify-content-between align-items-center mb-4">
          <div className="products-found">
            {!loading && (
              <p className="text-muted mb-0">
                Найдено товаров: <strong>{pagination.totalItems}</strong>
              </p>
            )}
          </div>
        </div>
        
        {error && (
          <div className="alert alert-danger" role="alert">
            {error}
          </div>
        )}
        
        {loading && (
          <div className="loading-overlay">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Загрузка...</span>
            </div>
          </div>
        )}
        
        {!loading && products.length === 0 ? (
          <div className="no-products">
            <p>Товары не найдены. Попробуйте изменить параметры фильтрации.</p>
          </div>
        ) : (
          <>
            <div className="product-cards row g-4">
              {products.map(product => (
                <div key={product.id} className="col-md-3">
                  <div className="product-card">
                    <Link to={`/products/${product.id}`} className="product-image-link">
                      <div className="product-image">
                        {product.image ? (
                          <img src={formatImageUrl(product.image)} alt={product.name} />
                        ) : (
                          <div className="no-image">Нет изображения</div>
                        )}
                      </div>
                    </Link>
                    <div className="product-details">
                      <Link to={`/products/${product.id}`} className="product-title-link">
                        <h3>{product.name}</h3>
                      </Link>
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

export default ProductsPage; 