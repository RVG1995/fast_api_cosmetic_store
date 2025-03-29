import React, { memo } from 'react';
import PropTypes from 'prop-types';
import { Form } from 'react-bootstrap';

/**
 * Универсальный компонент для полей формы с поддержкой валидации
 * и оптимизацией через React.memo
 */
const FormField = memo(({
  id,
  name,
  label,
  type = 'text',
  as,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  touched,
  className,
  disabled,
  readOnly,
  required,
  options,
  feedbackType = 'invalid',
  description,
  ...props
}) => {
  // Уникальный ID для поля (используем name, если id не передан)
  const fieldId = id || `field-${name}`;
  
  // Определяем, нужно ли показывать сообщение об ошибке
  const showError = !!error && (touched !== undefined ? touched : true);
  
  // Базовый рендер для текстовых полей, textarea, select, etc.
  const renderField = () => {
    // Базовые пропсы для компонента Form.Control
    const controlProps = {
      id: fieldId,
      name,
      type,
      placeholder,
      value: value || '',
      onChange,
      onBlur,
      isInvalid: showError,
      disabled,
      readOnly,
      required,
      className,
      ...props
    };

    // Если передан as, использовать его (например, textarea)
    if (as) {
      return <Form.Control as={as} {...controlProps} />;
    }

    // Для select создаем выпадающий список с опциями
    if (type === 'select') {
      return (
        <Form.Select {...controlProps}>
          {options?.map((option) => (
            <option 
              key={option.value} 
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </Form.Select>
      );
    }

    // Для checkbox и radio другая структура
    if (type === 'checkbox' || type === 'radio') {
      return (
        <Form.Check
          id={fieldId}
          name={name}
          type={type}
          label={label}
          checked={!!value}
          onChange={onChange}
          onBlur={onBlur}
          isInvalid={showError}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          className={className}
          {...props}
        />
      );
    }

    // По умолчанию возвращаем обычное текстовое поле
    return <Form.Control {...controlProps} />;
  };

  return (
    <Form.Group className="mb-3" controlId={fieldId}>
      {/* Не показываем label для checkbox/radio, т.к. он уже включен выше */}
      {type !== 'checkbox' && type !== 'radio' && label && (
        <Form.Label>
          {label}
          {required && <span className="text-danger ms-1">*</span>}
        </Form.Label>
      )}
      
      {/* Рендерим само поле ввода */}
      {renderField()}
      
      {/* Показываем описание поля, если оно есть */}
      {description && !showError && (
        <Form.Text className="text-muted">
          {description}
        </Form.Text>
      )}
      
      {/* Показываем сообщение об ошибке */}
      {showError && (
        <Form.Control.Feedback type={feedbackType}>
          {error}
        </Form.Control.Feedback>
      )}
    </Form.Group>
  );
});

FormField.displayName = 'FormField';

FormField.propTypes = {
  id: PropTypes.string,
  name: PropTypes.string.isRequired,
  label: PropTypes.node,
  type: PropTypes.string,
  as: PropTypes.string,
  placeholder: PropTypes.string,
  value: PropTypes.any,
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func,
  error: PropTypes.string,
  touched: PropTypes.bool,
  className: PropTypes.string,
  disabled: PropTypes.bool,
  readOnly: PropTypes.bool,
  required: PropTypes.bool,
  options: PropTypes.arrayOf(PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    label: PropTypes.string.isRequired,
    disabled: PropTypes.bool
  })),
  feedbackType: PropTypes.oneOf(['valid', 'invalid']),
  description: PropTypes.node
};

export default FormField; 