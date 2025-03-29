import { useState, useCallback } from 'react';

/**
 * Хук для форматирования значений полей ввода с поддержкой различных форматов
 * 
 * @param {string} initialValue - Начальное значение поля
 * @param {Object} options - Опции форматирования
 * @returns {Object} Методы для работы с форматированным значением
 */
function useFieldFormatter(initialValue = '', options = {}) {
  // Начальное значение форматируем при инициализации хука
  const [formattedValue, setFormattedValue] = useState(() => {
    return formatValue(initialValue, options);
  });
  
  // Форматирование значения на основе типа
  const formatValue = useCallback((value, opts = options) => {
    if (!value && value !== 0) return '';
    
    const { 
      type = 'text', 
      format, 
      mask, 
      prefix = '', 
      suffix = '',
      decimalPlaces,
      separator = ',',
      delimiter = '.',
      allowNegative = false
    } = opts;
    
    let formattedResult = String(value);
    
    // Применяем различные типы форматирования
    switch (type) {
      case 'phone':
        // Форматируем телефонный номер
        formattedResult = formatPhone(formattedResult, format || mask);
        break;
        
      case 'card':
        // Форматируем номер кредитной карты
        formattedResult = formatCreditCard(formattedResult);
        break;
        
      case 'date':
        // Форматируем дату
        formattedResult = formatDate(formattedResult, format || 'DD.MM.YYYY');
        break;
        
      case 'number':
        // Форматируем число
        formattedResult = formatNumber(
          formattedResult, 
          decimalPlaces, 
          separator, 
          delimiter, 
          allowNegative
        );
        break;
        
      case 'custom':
        // Применяем пользовательскую маску
        if (mask) {
          formattedResult = applyMask(formattedResult, mask);
        }
        break;
        
      default:
        // По умолчанию оставляем как есть
        break;
    }
    
    // Применяем префикс и суффикс
    return `${prefix}${formattedResult}${suffix}`;
  }, [options]);
  
  // Извлечение чистого значения без форматирования
  const extractRawValue = useCallback((formattedVal = formattedValue) => {
    const { 
      type = 'text', 
      prefix = '', 
      suffix = '',
      keepFormatChars = false
    } = options;
    
    // Удаляем префикс и суффикс
    let rawValue = formattedVal;
    if (prefix && rawValue.startsWith(prefix)) {
      rawValue = rawValue.substring(prefix.length);
    }
    if (suffix && rawValue.endsWith(suffix)) {
      rawValue = rawValue.substring(0, rawValue.length - suffix.length);
    }
    
    // В зависимости от типа очищаем форматирование
    switch (type) {
      case 'phone':
      case 'card':
        // Оставляем только цифры
        return keepFormatChars ? rawValue : rawValue.replace(/\D/g, '');
        
      case 'number':
        // Преобразуем в число
        const { separator = ',', delimiter = '.' } = options;
        const numberStr = rawValue
          .replace(new RegExp(`\\${separator}`, 'g'), '')
          .replace(new RegExp(`\\${delimiter}`, 'g'), '.');
        return numberStr;
        
      default:
        return rawValue;
    }
  }, [formattedValue, options]);
  
  // Обработчик изменения значения поля
  const handleChange = useCallback((e) => {
    const inputValue = e.target.value;
    const formattedResult = formatValue(inputValue);
    setFormattedValue(formattedResult);
    
    return {
      formattedValue: formattedResult,
      rawValue: extractRawValue(formattedResult)
    };
  }, [formatValue, extractRawValue]);
  
  // Обновление значения программно
  const updateValue = useCallback((newValue) => {
    const formattedResult = formatValue(newValue);
    setFormattedValue(formattedResult);
    
    return {
      formattedValue: formattedResult,
      rawValue: extractRawValue(formattedResult)
    };
  }, [formatValue, extractRawValue]);
  
  return {
    value: formattedValue,
    rawValue: extractRawValue(),
    handleChange,
    updateValue,
    formatValue,
    extractRawValue
  };
}

// Вспомогательные функции для форматирования

/**
 * Форматирует телефонный номер в соответствии с маской
 */
function formatPhone(value, format = '+7 (___) ___-__-__') {
  // Оставляем только цифры
  const digits = value.replace(/\D/g, '');
  let result = '';
  let digitIndex = 0;
  
  // Проходим по каждому символу формата
  for (let i = 0; i < format.length; i++) {
    if (format[i] === '_') {
      // Подставляем цифру, если она есть
      if (digitIndex < digits.length) {
        result += digits[digitIndex];
        digitIndex++;
      } else {
        // Если цифр больше нет, оставляем пустое место
        result += '_';
      }
    } else {
      // Добавляем символ из формата
      result += format[i];
    }
  }
  
  return result;
}

/**
 * Форматирует номер кредитной карты, группируя по 4 цифры
 */
function formatCreditCard(value) {
  const digits = value.replace(/\D/g, '');
  const groups = [];
  
  // Разбиваем на группы по 4 цифры
  for (let i = 0; i < digits.length; i += 4) {
    groups.push(digits.substring(i, i + 4));
  }
  
  return groups.join(' ');
}

/**
 * Форматирует дату в соответствии с форматом
 */
function formatDate(value, format) {
  // Оставляем только цифры
  const digits = value.replace(/\D/g, '');
  let result = format;
  
  // Заменяем метки DD, MM, YYYY на соответствующие цифры
  if (digits.length > 0) {
    const day = digits.substring(0, 2).padEnd(2, '_');
    result = result.replace('DD', day);
  }
  
  if (digits.length > 2) {
    const month = digits.substring(2, 4).padEnd(2, '_');
    result = result.replace('MM', month);
  }
  
  if (digits.length > 4) {
    const year = digits.substring(4, 8).padEnd(4, '_');
    result = result.replace('YYYY', year);
  }
  
  return result;
}

/**
 * Форматирует число с разделителями групп и дробной частью
 */
function formatNumber(value, decimalPlaces, separator, delimiter, allowNegative) {
  // Преобразуем в строку и обрабатываем отрицательные числа
  let numStr = String(value);
  const isNegative = numStr.startsWith('-');
  
  if (isNegative && !allowNegative) {
    numStr = numStr.substring(1);
  }
  
  // Разделяем на целую и дробную часть
  let [integerPart, fractionPart] = numStr.split('.');
  
  // Удаляем нецифровые символы из целой части
  integerPart = integerPart.replace(/\D/g, '');
  
  // Добавляем разделители групп
  integerPart = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, separator);
  
  // Обрабатываем дробную часть, если нужно
  if (decimalPlaces !== undefined) {
    if (fractionPart) {
      fractionPart = fractionPart.replace(/\D/g, '').slice(0, decimalPlaces);
    } else {
      fractionPart = '';
    }
    
    // Дополняем нулями, если необходимо
    if (fractionPart.length > 0 || decimalPlaces > 0) {
      fractionPart = fractionPart.padEnd(decimalPlaces, '0');
      return `${isNegative && allowNegative ? '-' : ''}${integerPart}${delimiter}${fractionPart}`;
    }
  }
  
  return `${isNegative && allowNegative ? '-' : ''}${integerPart}${fractionPart ? `${delimiter}${fractionPart}` : ''}`;
}

/**
 * Применяет произвольную маску к значению
 */
function applyMask(value, mask) {
  let result = '';
  let valueIndex = 0;
  
  for (let i = 0; i < mask.length; i++) {
    // Если встречаем специальный символ в маске
    if (mask[i] === '#') {
      // Подставляем символ из значения
      if (valueIndex < value.length) {
        result += value[valueIndex];
        valueIndex++;
      } else {
        // Если символов больше нет, оставляем пустое место
        result += '_';
      }
    } else {
      // Добавляем символ из маски
      result += mask[i];
    }
  }
  
  return result;
}

export default useFieldFormatter; 