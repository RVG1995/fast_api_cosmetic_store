import React, { useState, useEffect } from 'react';
import { productAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Link, useLocation, useNavigate } from 'react-router-dom';
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
      
      const response = await productAPI.getProducts(page, pagination.pageSize, activeFilters);
      console.log('API ответ продуктов:', response);
      
      // Обновляем товары и информацию о пагинации
      const { items, total, limit } = response.data;
      setProducts(Array.isArray(items) ? items : []);
      
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
    
    // Обновляем состояние фильтров
    setFilters(newFilters);
    
    // Устанавливаем новую страницу из URL или по умолчанию 1
    const page = parseInt(queryParams.get('page') || '1', 10);
    setPagination(prev => ({
      ...prev,
      currentPage: page
    }));
    
    // Загружаем товары с новыми фильтрами
    fetchProducts(page, newFilters);
  }, [location.search]);

  // Обновляем URL при изменении фильтров или страницы
  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.category_id) params.set('category_id', filters.category_id);
    if (filters.subcategory_id) params.set('subcategory_id', filters.subcategory_id);
    if (filters.brand_id) params.set('brand_id', filters.brand_id);
    if (filters.country_id) params.set('country_id', filters.country_id);
    if (pagination.currentPage > 1) params.set('page', pagination.currentPage.toString());
    
    navigate({ search: params.toString() }, { replace: true });
  }, [filters, pagination.currentPage, navigate]);

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

  // Обработчик сброса фильтров
  const handleResetFilters = () => {
    const emptyFilters = {
      category_id: '',
      subcategory_id: '',
      brand_id: '',
      country_id: '',
    };
    setFilters(emptyFilters);
    setPagination(prev => ({ ...prev, currentPage: 1 }));
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
          
          <div className="d-flex justify-content-end mt-3">
            <button 
              className="btn btn-secondary" 
              onClick={handleResetFilters}
            >
              Сбросить фильтры
            </button>
          </div>
        </div>
      </div>
    );
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
    <div className="home-page">
      <div className="container" style={{ maxWidth: '1200px' }}>
        <div className="product-header">
          <h2>Товары</h2>
          {hasAdminRights() && (
            <Link to="/admin/products" className="btn btn-primary">
              <i className="bi bi-gear-fill me-1"></i>
              Управление товарами
            </Link>
          )}
        </div>
        
        {/* Панель фильтров */}
        <FiltersPanel />
        
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