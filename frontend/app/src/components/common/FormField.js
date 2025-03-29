import React, { memo } from 'react';
import PropTypes from 'prop-types';
import './FormField.css';

/**
 * Компонент для отображения поля формы с меткой, подсказкой и сообщением об ошибке
 * Поддерживает различные типы полей ввода (text, password, email, etc.)
 */
const FormField = ({
  name,
  label,
  type = 'text',
  placeholder = '',
  value = '',
  error = null,
  touched = false,
  onChange,
  onBlur,
  className = '',
  labelClassName = '',
  inputClassName = '',
  errorClassName = '',
  helpText = '',
  disabled = false,
  required = false,
  readOnly = false,
  id = null,
  autoComplete = 'on',
  showError = true,
  options = [], // Для select и radio
  icon = null,  // Иконка Bootstrap
  iconPosition = 'right',
  ...props
}) => {
  // Генерируем уникальный ID для поля, если он не предоставлен
  const fieldId = id || `field-${name}`;
  
  // Определяем, нужно ли показывать ошибку
  const showErrorMessage = showError && touched && error;
  
  // Определяем CSS классы для обертки поля
  const wrapperClass = `form-field ${className} ${showErrorMessage ? 'has-error' : ''}`;
  
  // Определяем CSS классы для поля ввода
  const inputClass = `form-control ${inputClassName} ${showErrorMessage ? 'is-invalid' : touched ? 'is-valid' : ''}`;
  
  // Определяем CSS классы для метки
  const labelClass = `form-label ${labelClassName} ${required ? 'required' : ''}`;
  
  // Рендеринг поля в зависимости от типа
  const renderField = () => {
    // Общие пропсы для всех полей ввода
    const commonProps = {
      id: fieldId,
      name,
      value,
      onChange,
      onBlur,
      disabled,
      readOnly,
      required,
      className: inputClass,
      'aria-invalid': !!showErrorMessage,
      'aria-describedby': showErrorMessage ? `${fieldId}-error` : helpText ? `${fieldId}-help` : undefined,
      autoComplete,
      ...props,
    };

    // Отрисовка в зависимости от типа поля
    switch (type) {
      case 'textarea':
        return <textarea placeholder={placeholder} {...commonProps} />;
        
      case 'select':
        return (
          <select {...commonProps}>
            {placeholder && <option value="">{placeholder}</option>}
            {options.map((option, index) => (
              <option 
                key={option.value || index} 
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </option>
            ))}
          </select>
        );
        
      case 'checkbox':
        return (
          <div className="form-check">
            <input 
              type="checkbox" 
              className={`form-check-input ${showErrorMessage ? 'is-invalid' : touched ? 'is-valid' : ''}`}
              id={fieldId}
              name={name}
              checked={value}
              onChange={onChange}
              onBlur={onBlur}
              disabled={disabled}
              readOnly={readOnly}
              required={required}
            />
            {label && (
              <label className="form-check-label" htmlFor={fieldId}>
                {label}
              </label>
            )}
          </div>
        );
        
      case 'radio':
        return (
          <div className="form-field-radio">
            {options.map((option, index) => (
              <div className="form-check" key={option.value || index}>
                <input
                  type="radio"
                  className={`form-check-input ${showErrorMessage ? 'is-invalid' : touched ? 'is-valid' : ''}`}
                  id={`${fieldId}-${option.value}`}
                  name={name}
                  value={option.value}
                  checked={value === option.value}
                  onChange={onChange}
                  onBlur={onBlur}
                  disabled={option.disabled || disabled}
                  required={required}
                />
                <label className="form-check-label" htmlFor={`${fieldId}-${option.value}`}>
                  {option.label}
                </label>
              </div>
            ))}
          </div>
        );
        
      default: // text, password, email, number, etc.
        return (
          <div className={`form-field-input ${icon ? `has-icon icon-${iconPosition}` : ''}`}>
            <input
              type={type}
              placeholder={placeholder}
              {...commonProps}
            />
            {icon && (
              <span className="field-icon">
                <i className={`bi bi-${icon}`}></i>
              </span>
            )}
          </div>
        );
    }
  };

  return (
    <div className={wrapperClass}>
      {/* Метка (кроме чекбоксов, у которых она идет после) */}
      {label && type !== 'checkbox' && (
        <label htmlFor={fieldId} className={labelClass}>
          {label}
          {required && <span className="text-danger ms-1">*</span>}
        </label>
      )}
      
      {/* Поле ввода */}
      {renderField()}
      
      {/* Текст справки */}
      {helpText && (
        <div id={`${fieldId}-help`} className="form-text">
          {helpText}
        </div>
      )}
      
      {/* Сообщение об ошибке */}
      {showErrorMessage && (
        <div id={`${fieldId}-error`} className={`invalid-feedback ${errorClassName}`}>
          {error}
        </div>
      )}
    </div>
  );
};

FormField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.node,
  type: PropTypes.string,
  placeholder: PropTypes.string,
  value: PropTypes.any,
  error: PropTypes.string,
  touched: PropTypes.bool,
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func,
  className: PropTypes.string,
  labelClassName: PropTypes.string,
  inputClassName: PropTypes.string,
  errorClassName: PropTypes.string,
  helpText: PropTypes.node,
  disabled: PropTypes.bool,
  required: PropTypes.bool,
  readOnly: PropTypes.bool,
  id: PropTypes.string,
  autoComplete: PropTypes.string,
  showError: PropTypes.bool,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      label: PropTypes.node.isRequired,
      disabled: PropTypes.bool
    })
  ),
  icon: PropTypes.string,
  iconPosition: PropTypes.oneOf(['left', 'right'])
};

export default memo(FormField); 