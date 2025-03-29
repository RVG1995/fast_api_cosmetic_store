import React, { memo } from 'react';
import PropTypes from 'prop-types';
import './Form.css';

/**
 * Компонент-обертка для форм
 * Используется вместе с хуком useForm и компонентом FormField
 */
const Form = ({
  onSubmit,
  children,
  className = '',
  id = '',
  title = '',
  titleClassName = '',
  subtitle = '',
  submitButton = null,
  error = null,
  loading = false,
  disabled = false,
  validated = false,
  horizontal = false,
  compact = false,
  ...props
}) => {
  const formClassName = `
    custom-form 
    ${className} 
    ${validated ? 'was-validated' : ''} 
    ${horizontal ? 'form-horizontal' : ''} 
    ${compact ? 'form-compact' : ''}
  `;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit && !loading && !disabled) {
      onSubmit(e);
    }
  };

  return (
    <form
      className={formClassName}
      onSubmit={handleSubmit}
      noValidate
      id={id}
      {...props}
    >
      {title && (
        <h3 className={`form-title ${titleClassName}`}>{title}</h3>
      )}
      
      {subtitle && (
        <p className="form-subtitle">{subtitle}</p>
      )}
      
      {children}
      
      {error && (
        <div className="alert alert-danger mt-3" role="alert">
          {error}
        </div>
      )}
      
      {submitButton && (
        <div className="form-actions mt-4">
          {submitButton}
        </div>
      )}
    </form>
  );
};

Form.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  id: PropTypes.string,
  title: PropTypes.node,
  titleClassName: PropTypes.string,
  subtitle: PropTypes.node,
  submitButton: PropTypes.node,
  error: PropTypes.node,
  loading: PropTypes.bool,
  disabled: PropTypes.bool,
  validated: PropTypes.bool,
  horizontal: PropTypes.bool,
  compact: PropTypes.bool
};

export default memo(Form); 