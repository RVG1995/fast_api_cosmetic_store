import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Container, Row, Col, Card, Button, Spinner } from 'react-bootstrap';
import { useSearchParams } from 'react-router-dom';
import { productAPI } from '../utils/api';
import { useCategories } from '../context/CategoryContext';
import ErrorMessage from '../components/common/ErrorMessage';
import ProductCard from '../components/product/ProductCard';
import FilterSidebar from '../components/filters/FilterSidebar';
import Pagination from '../components/common/Pagination';
import '../styles/ProductsPage.css';
import { useReviews } from '../context/ReviewContext';

/**
 * Страница со списком товаров и фильтрацией
 */
const ProductsPage = () => {
  const { categories } = useCategories();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Состояние для данных
  const [products, setProducts] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [subcategories, setSubcategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [countries, setCountries] = useState([]);
  
  const { fetchBatchProductRatings } = useReviews();
  
  // Параметры фильтрации и сортировки
  const filters = useMemo(() => ({
    category_id: searchParams.get('category_id') || '',
    subcategory_id: searchParams.get('subcategory_id') || '',
    brand_id: searchParams.get('brand_id') || '',
    country_id: searchParams.get('country_id') || '',
    min_price: searchParams.get('min_price') || '',
    max_price: searchParams.get('max_price') || '',
    is_available: searchParams.get('in_stock') === 'true',
    search: searchParams.get('search') || '',
    sort: searchParams.get('sort') || 'name_asc',
    page: parseInt(searchParams.get('page') || '1', 10),
    limit: parseInt(searchParams.get('limit') || '12', 10)
  }), [searchParams]);
  
  // Загрузка вспомогательных данных
  useEffect(() => {
    const loadFilterData = async () => {
      try {
        const [subcategoriesRes, brandsRes, countriesRes] = await Promise.all([
          productAPI.getSubcategories(),
          productAPI.getBrands(),
          productAPI.getCountries()
        ]);
        
        setSubcategories(subcategoriesRes.data || []);
        setBrands(brandsRes.data || []);
        setCountries(countriesRes.data || []);
      } catch (err) {
        console.error('Ошибка при загрузке данных для фильтров:', err);
      }
    };
    
    loadFilterData();
  }, []);
  
  // Обработчик изменения фильтров
  const handleFilterChange = useCallback((name, value) => {
    setSearchParams(prev => {
      if (value === '' || value === null) {
        prev.delete(name);
      } else {
        prev.set(name, value);
      }
      // При изменении фильтрации сбрасываем страницу на первую
      if (name !== 'page') {
        prev.set('page', '1');
      }
      return prev;
    });
  }, [setSearchParams]);
  
  // Загрузка товаров с учетом фильтров
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Формируем параметры запроса из фильтров
      const queryParams = {};
      
      if (filters.category_id) queryParams.category_id = filters.category_id;
      if (filters.subcategory_id) queryParams.subcategory_id = filters.subcategory_id;
      if (filters.brand_id) queryParams.brand_id = filters.brand_id;
      if (filters.country_id) queryParams.country_id = filters.country_id;
      if (filters.min_price) queryParams.min_price = filters.min_price;
      if (filters.max_price) queryParams.max_price = filters.max_price;
      if (filters.is_available) queryParams.is_available = filters.is_available;
      if (filters.search) queryParams.search = filters.search;
      
      // Сортировка
      const [sortField, sortOrder] = filters.sort.split('_');
      queryParams.sort_by = sortField;
      queryParams.sort_order = sortOrder;
      
      // Пагинация
      queryParams.page = filters.page;
      queryParams.limit = filters.limit;
      
      const response = await productAPI.getProducts(
        filters.page,
        filters.limit,
        queryParams,
        filters.sort
      );
      
      if (response && response.data) {
        setProducts(response.data.items || []);
        setTotalProducts(response.data.total || 0);
      } else {
        setError('Ошибка при загрузке товаров: неверный формат ответа');
      }
    } catch (err) {
      setError('Не удалось загрузить товары. Пожалуйста, попробуйте позже.');
      console.error('Error fetching products:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);
  
  // Загружаем товары при изменении фильтров
  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);
  
  // После загрузки списка товаров, загружаем их рейтинги
  useEffect(() => {
    if (products && products.length > 0) {
      // Извлекаем ID товаров из списка
      const productIds = products.map(product => product.id);
      // Загружаем рейтинги пакетно
      fetchBatchProductRatings(productIds);
    }
  }, [products, fetchBatchProductRatings]);
  
  // Подсчет количества страниц
  const totalPages = useMemo(() => 
    Math.ceil(totalProducts / filters.limit), 
    [totalProducts, filters.limit]
  );
  
  // Обработчик изменения страницы
  const handlePageChange = useCallback((page) => {
    handleFilterChange('page', page.toString());
  }, [handleFilterChange]);
  
  // Обработчик сброса фильтров
  const handleResetFilters = useCallback(() => {
    setSearchParams({});
  }, [setSearchParams]);
  
  return (
    <Container className="products-page py-4">
      <h1 className="mb-4">Каталог товаров</h1>
      
      <Row>
        {/* Фильтры */}
        <Col lg={3} className="filters-wrapper mb-4">
          <Card className="filter-card">
            <Card.Body>
              <FilterSidebar
                filters={filters}
                categories={categories}
                subcategories={subcategories}
                brands={brands}
                countries={countries}
                onFilterChange={handleFilterChange}
                onResetFilters={handleResetFilters}
              />
            </Card.Body>
          </Card>
        </Col>
        
        {/* Список товаров */}
        <Col lg={9}>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              {!loading && !error && (
                <p className="text-muted mb-0">
                  Найдено товаров: {totalProducts}
                </p>
              )}
            </div>
          </div>
          
          {loading ? (
            <div className="text-center py-5">
              <Spinner animation="border" variant="primary" />
              <p className="mt-2">Загрузка товаров...</p>
            </div>
          ) : error ? (
            <ErrorMessage message={error} />
          ) : products.length === 0 ? (
            <div className="text-center py-5">
              <i className="bi bi-search fs-1 text-muted"></i>
              <h4 className="mt-3">Товары не найдены</h4>
              <p className="text-muted">
                Попробуйте изменить параметры поиска или фильтрации.
              </p>
              <Button variant="outline-primary" onClick={handleResetFilters}>
                Сбросить все фильтры
              </Button>
            </div>
          ) : (
            <>
              <Row xs={1} sm={2} md={2} lg={3} className="g-4 mb-4">
                {products.map(product => (
                  <Col key={product.id}>
                    <ProductCard product={product} />
                  </Col>
                ))}
              </Row>
              
              {/* Пагинация */}
              {totalPages > 1 && (
                <div className="d-flex justify-content-center mt-4">
                  <Pagination
                    currentPage={filters.page}
                    totalPages={totalPages}
                    onPageChange={handlePageChange}
                  />
                </div>
              )}
            </>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default ProductsPage;