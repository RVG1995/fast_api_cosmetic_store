import React, { memo } from 'react';
import { Form } from 'react-bootstrap';
import PropTypes from 'prop-types';

/**
 * Компонент для выбора опций сортировки списка товаров
 * @param {Object} props - Свойства компонента
 * @param {string} props.value - Текущее значение сортировки
 * @param {function} props.onChange - Обработчик изменения сортировки
 * @param {string} props.className - Дополнительные CSS классы
 */
const SortOptions = memo(({ value = 'price_asc', onChange, className = '' }) => {
  const handleChange = (e) => {
    onChange(e.target.value);
  };
  
  return (
    <Form.Group className={`sort-options ${className}`}>
      <Form.Select 
        value={value} 
        onChange={handleChange}
        aria-label="Сортировка товаров"
      >
        <option value="price_asc">По цене (сначала дешевле)</option>
        <option value="price_desc">По цене (сначала дороже)</option>
      </Form.Select>
    </Form.Group>
  );
});

SortOptions.displayName = 'SortOptions';

SortOptions.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  className: PropTypes.string
};

export default SortOptions; 