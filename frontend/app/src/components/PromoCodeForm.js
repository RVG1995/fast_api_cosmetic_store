import React, { useState } from 'react';
import { Form, InputGroup, Button, Alert } from 'react-bootstrap';
import { useOrders } from '../context/OrderContext';
import { formatPrice } from '../utils/helpers';

const PromoCodeForm = ({ email, phone, cartTotal, onPromoCodeApplied }) => {
  const [promoCodeInput, setPromoCodeInput] = useState('');
  const { checkPromoCode, promoCode, clearPromoCode, calculateDiscount, loading, error } = useOrders();
  const [validationErrors, setValidationErrors] = useState(null);
  
  // Обработчик изменения поля ввода промокода
  const handlePromoCodeChange = (e) => {
    setPromoCodeInput(e.target.value);
    // Сбрасываем ошибки валидации при изменении ввода
    setValidationErrors(null);
  };
  
  // Функция для валидации полей
  const validateFields = () => {
    const errors = [];
    
    // Проверка email
    if (!email || email.trim() === '') {
      errors.push('Введите email для проверки промокода');
    } else if (!email.includes('@')) {
      errors.push('Введите корректный email');
    }
    
    // Проверка номера телефона
    if (!phone || phone.trim() === '') {
      errors.push('Введите номер телефона для проверки промокода');
    } else if (phone.length < 11) {
      errors.push('Номер телефона должен содержать не менее 11 символов');
    }
    
    // Проверка промокода
    if (!promoCodeInput || promoCodeInput.trim() === '') {
      errors.push('Введите промокод');
    }
    
    if (errors.length > 0) {
      setValidationErrors(errors);
      return false;
    }
    
    return true;
  };
  
  // Обработчик применения промокода
  const handleApplyPromoCode = async (e) => {
    e.preventDefault();
    
    // Сбрасываем предыдущие ошибки
    setValidationErrors(null);
    
    // Валидация полей перед отправкой запроса
    if (!validateFields()) {
      return;
    }
    
    console.log('Отправляем запрос на проверку промокода:', promoCodeInput, email, phone);
    
    // Проверяем промокод через API
    const result = await checkPromoCode(promoCodeInput, email, phone);
    
    if (result && result.is_valid) {
      console.log('Промокод успешно проверен:', result);
      
      // Рассчитываем скидку самостоятельно, не полагаясь на calculateDiscount из контекста
      let discount = 0;
      if (result.discount_percent) {
        // Скидка в процентах
        discount = Math.floor(cartTotal * result.discount_percent / 100);
      } else if (result.discount_amount) {
        // Фиксированная скидка
        discount = Math.min(result.discount_amount, cartTotal);
      }
      
      console.log('Скидка рассчитана:', discount, 'из общей суммы:', cartTotal, 'процент скидки:', result.discount_percent, 'ID промокода:', result.promo_code?.id);
      
      // Оповещаем родительский компонент о применении промокода
      if (onPromoCodeApplied) {
        const promoData = {
          code: promoCodeInput,
          discount,
          discountPercent: result.discount_percent,
          discountAmount: result.discount_amount,
          promoCodeId: result.promo_code?.id
        };
        console.log('Передаем данные о промокоде:', promoData);
        onPromoCodeApplied(promoData);
      }
    } else {
      console.log('Промокод не валиден:', result);
    }
  };
  
  // Обработчик удаления промокода
  const handleRemovePromoCode = () => {
    // Очищаем промокод
    clearPromoCode();
    setPromoCodeInput('');
    setValidationErrors(null);
    
    // Оповещаем родительский компонент об удалении промокода
    if (onPromoCodeApplied) {
      onPromoCodeApplied(null);
    }
  };
  
  return (
    <div className="promo-code-form mb-3">
      <h5>Промокод</h5>
      {promoCode ? (
        <div className="applied-promo-code">
          <Alert variant="success" className="d-flex justify-content-between align-items-center">
            <div>
              <strong>Промокод применен: {promoCode.code}</strong>
              <div>
                {promoCode.discountPercent ? (
                  <span>Скидка {promoCode.discountPercent}%</span>
                ) : (
                  <span>Скидка {formatPrice(promoCode.discountAmount)} ₽</span>
                )}
                {cartTotal > 0 && (
                  <span className="ms-2">({formatPrice(calculateDiscount(cartTotal))} ₽)</span>
                )}
              </div>
            </div>
            <Button 
              variant="outline-danger" 
              size="sm"
              onClick={handleRemovePromoCode}
              disabled={loading}
            >
              Удалить
            </Button>
          </Alert>
        </div>
      ) : (
        <Form onSubmit={handleApplyPromoCode}>
          <InputGroup>
            <Form.Control
              type="text"
              placeholder="Введите промокод"
              value={promoCodeInput}
              onChange={handlePromoCodeChange}
              disabled={loading}
            />
            <Button 
              variant="outline-primary" 
              type="submit"
              disabled={loading || !promoCodeInput.trim()}
            >
              {loading ? 'Проверка...' : 'Применить'}
            </Button>
          </InputGroup>
          
          {/* Отображение ошибок валидации */}
          {validationErrors && validationErrors.length > 0 && (
            <Alert variant="danger" className="mt-2">
              <ul className="mb-0 ps-3">
                {validationErrors.map((err, index) => (
                  <li key={index}>{err}</li>
                ))}
              </ul>
            </Alert>
          )}
          
          {/* Отображение ошибок от API */}
          {error && !validationErrors && (
            <Alert variant="danger" className="mt-2">
              {error}
            </Alert>
          )}
        </Form>
      )}
    </div>
  );
};

export default PromoCodeForm; 