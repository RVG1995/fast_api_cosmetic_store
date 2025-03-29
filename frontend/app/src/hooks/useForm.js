import { useState, useCallback, useEffect } from 'react';

/**
 * Хук для управления формами с валидацией
 * 
 * @param {Object} initialValues - Начальные значения формы
 * @param {Function} validateFn - Функция валидации, возвращающая объект с ошибками
 * @param {Function} onSubmit - Функция, вызываемая при успешной отправке формы
 * @returns {Object} Объект с состоянием и методами управления формой
 */
function useForm(initialValues = {}, validateFn = () => ({}), onSubmit = () => {}) {
  // Состояние значений формы
  const [values, setValues] = useState(initialValues);
  
  // Состояние ошибок
  const [errors, setErrors] = useState({});
  
  // Состояние касания полей (для отображения ошибок только после касания)
  const [touched, setTouched] = useState({});
  
  // Состояние отправки формы
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Состояние успешной отправки
  const [isSubmitted, setIsSubmitted] = useState(false);
  
  // Была ли форма изменена
  const [isDirty, setIsDirty] = useState(false);

  // Проверка, валидна ли форма
  const isValid = Object.keys(errors).length === 0;

  // Валидация формы при изменении значений
  useEffect(() => {
    if (isDirty) {
      const validationErrors = validateFn(values);
      setErrors(validationErrors);
    }
  }, [values, validateFn, isDirty]);

  // Обработчик изменения значения поля
  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    
    // Для чекбоксов используем состояние checked вместо value
    const fieldValue = type === 'checkbox' ? checked : value;
    
    setValues(prevValues => ({
      ...prevValues,
      [name]: fieldValue
    }));
    
    setIsDirty(true);
  }, []);

  // Обработчик касания поля
  const handleBlur = useCallback((e) => {
    const { name } = e.target;
    
    setTouched(prevTouched => ({
      ...prevTouched,
      [name]: true
    }));
  }, []);

  // Ручное изменение значения поля
  const setValue = useCallback((name, value) => {
    setValues(prevValues => ({
      ...prevValues,
      [name]: value
    }));
    
    setIsDirty(true);
  }, []);

  // Ручное изменение нескольких значений
  const setMultipleValues = useCallback((newValues) => {
    setValues(prevValues => ({
      ...prevValues,
      ...newValues
    }));
    
    setIsDirty(true);
  }, []);

  // Сброс формы к начальным значениям
  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
    setIsSubmitted(false);
    setIsDirty(false);
  }, [initialValues]);

  // Установка всех полей как затронутых
  const touchAll = useCallback(() => {
    const touchedFields = Object.keys(values).reduce((acc, key) => {
      acc[key] = true;
      return acc;
    }, {});
    
    setTouched(touchedFields);
  }, [values]);

  // Отправка формы
  const handleSubmit = useCallback(async (e) => {
    if (e) e.preventDefault();
    
    // Помечаем все поля как затронутые
    touchAll();
    
    // Проверяем наличие ошибок
    const validationErrors = validateFn(values);
    setErrors(validationErrors);
    
    // Если есть ошибки, прерываем отправку
    if (Object.keys(validationErrors).length > 0) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      await onSubmit(values);
      setIsSubmitted(true);
    } catch (error) {
      // Если onSubmit выбросил ошибку, можем обработать её здесь
      console.error('Form submission error:', error);
      
      // Если ошибка содержит поля формы с ошибками
      if (error.fieldErrors) {
        setErrors(prev => ({
          ...prev,
          ...error.fieldErrors
        }));
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [values, validateFn, onSubmit, touchAll]);

  // Получение свойств для поля ввода
  const getFieldProps = useCallback((name) => {
    return {
      name,
      value: values[name] !== undefined ? values[name] : '',
      onChange: handleChange,
      onBlur: handleBlur,
      error: touched[name] && errors[name]
    };
  }, [values, handleChange, handleBlur, touched, errors]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isSubmitted,
    isDirty,
    isValid,
    handleChange,
    handleBlur,
    handleSubmit,
    setValue,
    setMultipleValues,
    resetForm,
    touchAll,
    getFieldProps
  };
}

export default useForm; 