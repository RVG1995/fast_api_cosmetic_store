import React, { useMemo } from 'react';
import { Form, Button } from 'react-bootstrap';
import PropTypes from 'prop-types';
import SortOptions from './SortOptions';

/**
 * Компонент боковой панели фильтров для страницы товаров
 */
const FilterSidebar = ({ 
  filters, 
  categories = [], 
  subcategories = [], 
  brands = [], 
  countries = [], 
  onFilterChange, 
  onResetFilters 
}) => {
  // Фильтруем подкатегории соответствующие выбранной категории
  const filteredSubcategories = useMemo(() => {
    if (!filters.category_id) return [];
    return subcategories.filter(sub => 
      sub.category_id === parseInt(filters.category_id, 10)
    );
  }, [filters.category_id, subcategories]);
  
  // Обработчик изменения категории
  const handleCategoryChange = (e) => {
    const categoryId = e.target.value;
    // При смене категории сбрасываем подкатегорию
    onFilterChange('category_id', categoryId);
    onFilterChange('subcategory_id', '');
  };
  
  // Обработчик сортировки
  const handleSortChange = (sortValue) => {
    onFilterChange('sort', sortValue);
  };
  
  // Сброс всех фильтров
  const resetFilters = () => {
    onResetFilters();
  };
  
  return (
    <div className="filter-sidebar">
      <h5 className="mb-3">Фильтры товаров</h5>
      
      {/* Сортировка */}
      <Form.Group className="mb-3">
        <Form.Label>Сортировка</Form.Label>
        <SortOptions 
          value={filters.sort} 
          onChange={handleSortChange}
        />
      </Form.Group>
      
      {/* Категории */}
      <Form.Group className="mb-3">
        <Form.Label>Категория</Form.Label>
        <Form.Select 
          value={filters.category_id} 
          onChange={handleCategoryChange}
        >
          <option value="">Все категории</option>
          {categories.map(category => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </Form.Select>
      </Form.Group>
      
      {/* Подкатегории */}
      <Form.Group className="mb-3">
        <Form.Label>Подкатегория</Form.Label>
        <Form.Select 
          value={filters.subcategory_id} 
          onChange={(e) => onFilterChange('subcategory_id', e.target.value)}
          disabled={!filters.category_id || filteredSubcategories.length === 0}
        >
          <option value="">Все подкатегории</option>
          {filteredSubcategories.map(subcategory => (
            <option key={subcategory.id} value={subcategory.id}>
              {subcategory.name}
            </option>
          ))}
        </Form.Select>
      </Form.Group>
      
      {/* Бренды */}
      <Form.Group className="mb-3">
        <Form.Label>Бренд</Form.Label>
        <Form.Select 
          value={filters.brand_id} 
          onChange={(e) => onFilterChange('brand_id', e.target.value)}
        >
          <option value="">Все бренды</option>
          {brands.map(brand => (
            <option key={brand.id} value={brand.id}>
              {brand.name}
            </option>
          ))}
        </Form.Select>
      </Form.Group>
      
      {/* Страны */}
      <Form.Group className="mb-3">
        <Form.Label>Страна производства</Form.Label>
        <Form.Select 
          value={filters.country_id} 
          onChange={(e) => onFilterChange('country_id', e.target.value)}
        >
          <option value="">Все страны</option>
          {countries.map(country => (
            <option key={country.id} value={country.id}>
              {country.name}
            </option>
          ))}
        </Form.Select>
      </Form.Group>
      
      {/* Кнопка сброса */}
      <Button 
        variant="secondary" 
        className="btn-reset"
        onClick={resetFilters}
      >
        Сбросить все фильтры
      </Button>
    </div>
  );
};

FilterSidebar.propTypes = {
  filters: PropTypes.object.isRequired,
  categories: PropTypes.array,
  subcategories: PropTypes.array,
  brands: PropTypes.array,
  countries: PropTypes.array,
  onFilterChange: PropTypes.func.isRequired,
  onResetFilters: PropTypes.func.isRequired
};

export default FilterSidebar; 