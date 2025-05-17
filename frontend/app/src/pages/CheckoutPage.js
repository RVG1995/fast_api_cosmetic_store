import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useOrders } from '../context/OrderContext';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Form, Card, Row, Col, Spinner } from 'react-bootstrap';
import { formatPrice } from '../utils/helpers';
import PromoCodeForm from '../components/PromoCodeForm';
import BoxberryPickupModal from '../components/cart/BoxberryPickupModal';
import './CheckoutPage.css';
import axios from 'axios';
import { API_URLS } from '../utils/constants';
import { deliveryAPI } from '../utils/api';

// Функция для склонения слова "день" в зависимости от числа
const getDeliveryPeriodText = (days) => {
  const cases = [2, 0, 1, 1, 1, 2];
  const titles = ['день', 'дня', 'дней'];
  
  if (days % 100 > 4 && days % 100 < 20) {
    return titles[2];
  } else {
    return titles[cases[Math.min(days % 10, 5)]];
  }
};

const CheckoutPage = () => {
  const navigate = useNavigate();
  const { cart, clearCart } = useCart();
  const { createOrder, loading, error, setError, promoCode, clearPromoCode } = useOrders();
  const { user } = useAuth();
  
  // Состояния формы
  const [formData, setFormData] = useState({
    fullName: user?.full_name || '',
    email: user?.email || '',
    phone: '',
    delivery_address: '',
    comment: '',
    personalDataAgreement: false,
    receiveNotifications: true, // По умолчанию согласие на получение уведомлений для неавторизованных пользователей
    paymentMethod: true // По умолчанию оплата при получении
  });
  
  const [validated, setValidated] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);
  const [orderNumber, setOrderNumber] = useState(null);
  const [redirectTimer, setRedirectTimer] = useState(null);
  const [cartTotal, setCartTotal] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);
  const [nameSuggestions, setNameSuggestions] = useState([]);
  // Подсказки адресов
  const [addressOptions, setAddressOptions] = useState([]);
  
  // Состояния для BoxBerry
  const [showBoxberryModal, setShowBoxberryModal] = useState(false);
  const [selectedPickupPoint, setSelectedPickupPoint] = useState(null);
  const [isBoxberryDelivery, setIsBoxberryDelivery] = useState(false);
  
  // Состояния для доставки
  const [deliveryType, setDeliveryType] = useState('');
  const [deliveryCost, setDeliveryCost] = useState(0);
  const [calculatingDelivery, setCalculatingDelivery] = useState(false);
  const [deliveryError, setDeliveryError] = useState(null);
  const [isPaymentOnDelivery, setIsPaymentOnDelivery] = useState(true); // По умолчанию оплата при получении
  const [deliveryPeriod, setDeliveryPeriod] = useState(0); // Добавляем состояние для срока доставки
  
  // Состояния для адреса доставки (для курьерской доставки)
  const [selectedAddressData, setSelectedAddressData] = useState(null);
  
  // Блокировка для предотвращения параллельных запросов
  const [isCalculating, setIsCalculating] = useState(false);
  
  // Состояние для отслеживания недоступных типов доставки
  const [disabledDeliveryTypes, setDisabledDeliveryTypes] = useState([]);
  
  // Проверяем наличие товаров в корзине и вычисляем общую стоимость
  useEffect(() => {
    // Если заказ успешно создан, не выполняем редирект даже при пустой корзине
    if (orderSuccess) {
      return;
    }
    
    if (!cart || !cart.items || cart.items.length === 0) {
      navigate('/cart');
    } else {
      // Вычисляем общую стоимость корзины
      const total = cart.items.reduce((sum, item) => {
        return sum + (item.product?.price || 0) * item.quantity;
      }, 0);
      setCartTotal(total);
    }
  }, [cart, navigate, orderSuccess]);
  
  // Вычисляем итоговую сумму с учетом скидки и стоимости доставки
  const finalTotal = cartTotal - discountAmount + deliveryCost;
  
  // Функция для расчета стоимости доставки
  // Принимает параметр forcePaymentOnDelivery, который позволяет передать значение напрямую
  // вместо получения из состояния, которое может не успеть обновиться
  const calculateDeliveryCost = async (forcePaymentOnDelivery = null) => {
    // Проверяем, нет ли уже запущенного расчета
    if (isCalculating) {
      console.log('Расчет доставки уже выполняется, запрос пропущен');
      return;
    }
    
    // Используем параметр forcePaymentOnDelivery, если он передан, иначе берем из состояния
    const paymentOnDelivery = forcePaymentOnDelivery !== null ? forcePaymentOnDelivery : isPaymentOnDelivery;
    
    console.log('Запуск расчета доставки с параметрами:', {
      deliveryType,
      isPaymentOnDelivery: paymentOnDelivery,
      currentStateValue: isPaymentOnDelivery,
      hasPVZ: !!selectedPickupPoint,
      hasAddressData: !!selectedAddressData
    });
    
    // Если нет выбранного типа доставки, не выполняем расчет
    if (!deliveryType) {
      setDeliveryCost(0);
      return;
    }
    
    // Проверяем, что выбран сервис Boxberry
    const isBoxberry = deliveryType.startsWith('boxberry_');
    if (!isBoxberry) {
      // Для не-Boxberry сервисов не выполняем расчет
      setDeliveryCost(0);
      return;
    }
    
    // Проверяем наличие необходимых данных для расчета
    if (deliveryType === 'boxberry_pickup_point') {
      // Обязательно нужен выбранный пункт для Boxberry ПВЗ
      if (!selectedPickupPoint) {
        console.log('Не хватает данных для расчета: не выбран пункт выдачи');
        return;
      }
    } else if (deliveryType === 'boxberry_courier') {
      // Для курьерской доставки Boxberry нужен адрес
      if (!formData.delivery_address || !selectedAddressData) {
        console.log('Не хватает данных для расчета: не указан адрес доставки или нет данных адреса', {
          address: formData.delivery_address,
          addressData: selectedAddressData
        });
        return;
      }
      
      // Проверяем, что у нас есть почтовый индекс, без которого невозможно рассчитать курьерскую доставку
      if (!selectedAddressData.postal_code) {
        console.log('Не удалось определить почтовый индекс для адреса');
        setDeliveryError('Не удалось определить почтовый индекс для адреса. Выберите адрес из списка подсказок.');
        return;
      }
    }
    
    try {
      setIsCalculating(true);
      setCalculatingDelivery(true);
      setDeliveryError(null);
      
      // Формируем предположительные данные о товарах в корзине для расчета
      const cartItems = cart.items.map(item => ({
        product_id: item.product.id,
        quantity: item.quantity,
        price: item.product.price,
        weight: item.product.weight || 500, // Используем вес товара или 500г по умолчанию
        height: item.product.height || 10,   // Используем высоту товара или 10см по умолчанию
        width: item.product.width || 10,    // Используем ширину товара или 10см по умолчанию
        depth: item.product.depth || 10     // Используем глубину товара или 10см по умолчанию
      }));
      
      // Данные для отправки на сервер
      const deliveryData = {
        items: cartItems,
        delivery_type: deliveryType,
        is_payment_on_delivery: paymentOnDelivery // Используем актуальное значение
      };
      
      // Если выбран пункт выдачи BoxBerry, добавляем его код
      if (deliveryType === 'boxberry_pickup_point' && selectedPickupPoint) {
        deliveryData.pvz_code = selectedPickupPoint.Code;
      }
      
      // Если выбрана курьерская доставка и есть данные адреса, добавляем почтовый индекс
      if (deliveryType === 'boxberry_courier' && selectedAddressData) {
        // Почтовый индекс - ключевой параметр для расчета курьерской доставки
        if (selectedAddressData.postal_code) {
          deliveryData.zip_code = selectedAddressData.postal_code;
        }
        
        // Добавляем название населенного пункта (город или поселок)
        if (selectedAddressData.city) {
          deliveryData.city_name = selectedAddressData.city;
        }
        
        console.log('Данные адреса для расчета:', {
          zip_code: selectedAddressData.postal_code, 
          city: selectedAddressData.city
        });
      }
      
      console.log('Отправляем запрос на расчет доставки:', deliveryData);
      
      // Вызываем API для расчета стоимости доставки
      const result = await deliveryAPI.calculateDeliveryFromCart(deliveryData);
      
      // Устанавливаем полученную стоимость доставки
      setDeliveryCost(result.price);
      setDeliveryPeriod(result.delivery_period);
      console.log('Рассчитана стоимость доставки:', result.price);
      console.log('Срок доставки (дней):', result.delivery_period);
      
    } catch (err) {
      console.error('Ошибка при расчете стоимости доставки:', err);
      // Проверяем наличие детальной информации об ошибке от API
      if (err.response && err.response.data && err.response.data.detail) {
        // Устанавливаем текст ошибки из ответа API
        setDeliveryError(err.response.data.detail);
        
        // Если ошибка связана с невозможностью курьерской доставки
        const errorText = err.response.data.detail.toLowerCase();
        if (errorText.includes('курьерская доставка') && errorText.includes('невозможна')) {
          console.log('Курьерская доставка невозможна по указанному адресу/индексу');
          
          // Блокируем выбор курьерской доставки, если она невозможна по указанному адресу
          if (deliveryType === 'boxberry_courier') {
            // Добавляем тип доставки в список недоступных
            setDisabledDeliveryTypes(prev => [...prev.filter(type => type !== 'boxberry_courier'), 'boxberry_courier']);
            
            // Сбрасываем тип доставки на пустой
            setDeliveryType('');
            
            // Показываем конкретное сообщение об ошибке
            setDeliveryError(`Курьерская доставка невозможна по указанному адресу/индексу. Пожалуйста, выберите другой способ доставки или адрес.`);
          }
        }
      } else {
        setDeliveryError('Не удалось рассчитать стоимость доставки');
      }
      setDeliveryCost(0);
    } finally {
      setCalculatingDelivery(false);
      setIsCalculating(false);
    }
  };
  
  // Функция для отложенного выполнения расчета доставки
  const debouncedCalculateDelivery = useCallback(
    (() => {
      let timer = null;
      return (address) => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
          if (address && address.length > 5 && deliveryType === 'boxberry_courier') {
            calculateDeliveryCost();
          }
        }, 1000); // Задержка в 1 секунду
      };
    })(),
    [deliveryType, isPaymentOnDelivery, cart]
  );
  
  // Вызываем расчет стоимости доставки только при изменении типа доставки, 
  // пункта выдачи или данных адреса, но НЕ при изменении способа оплаты
  useEffect(() => {
    // Расчет при изменении способа оплаты происходит в обработчиках
    // событий радиокнопок, поэтому здесь не следим за isPaymentOnDelivery
    
    console.log('Изменились параметры для расчета доставки:', { 
      deliveryType, 
      selectedPoint: selectedPickupPoint?.Code,
      postal_code: selectedAddressData?.postal_code,
      itemsCount: cart?.items?.length
    });
    
    // Запускаем расчет в следующих случаях:
    // 1) Выбран пункт выдачи для Boxberry ПВЗ
    // 2) Выбрана курьерская доставка Boxberry и есть данные адреса с индексом
    // 3) Выбран другой тип доставки (не Boxberry)
    if (
      (deliveryType === 'boxberry_pickup_point' && selectedPickupPoint) ||
      (deliveryType === 'boxberry_courier' && selectedAddressData && selectedAddressData.postal_code) ||
      (!deliveryType.startsWith('boxberry_'))
    ) {
      // Используем текущее значение isPaymentOnDelivery
      calculateDeliveryCost();
    }
  }, [deliveryType, selectedPickupPoint, selectedAddressData, cart]); // Убрали isPaymentOnDelivery из зависимостей
  
  // Функция запроса подсказок FIO через axios с логами
  const fetchNameSuggestions = async (query) => {
    console.log('Dadata FIO fetch:', query);
    if (!query) return setNameSuggestions([]);
    try {
      const { data } = await axios.post(
        `${API_URLS.DELIVERY_SERVICE}/delivery/dadata/fio`,
        { query }
      );
      console.log('Dadata FIO resp:', data.suggestions);
      const values = data.suggestions.map(s => s.value);
      setNameSuggestions(values);
    } catch (e) {
      console.error('DaData FIO error', e);
    }
  };

  // Подсказки адресов
  const fetchAddressSuggestions = async (query) => {
    console.log('Dadata address fetch:', query);
    if (!query) {
      setAddressOptions([]);
      return;
    }
    try {
      const { data } = await axios.post(
        `${API_URLS.DELIVERY_SERVICE}/delivery/dadata/address`,
        { query }
      );
      console.log('Dadata address resp:', data.suggestions);
      setAddressOptions(data.suggestions);
      
      // Если есть результаты и выбрана курьерская доставка BoxBerry, 
      // используем первый (наиболее релевантный) результат
      if (data.suggestions && data.suggestions.length > 0 && deliveryType === 'boxberry_courier') {
        const bestMatch = data.suggestions[0];
        
        // Автоматически устанавливаем данные адреса из лучшего совпадения
        // Это позволит выполнить расчет, даже если пользователь не выберет из выпадающего списка
        setSelectedAddressData({
          value: bestMatch.value,
          postal_code: bestMatch.data.postal_code,
          city: bestMatch.data.city || bestMatch.data.settlement, // Используем название поселка, если город не указан
          settlement: bestMatch.data.settlement,
          street: bestMatch.data.street,
          house: bestMatch.data.house
        });
        
        console.log('Автоматически выбраны данные адреса:', {
          value: bestMatch.value,
          postal_code: bestMatch.data.postal_code,
          city: bestMatch.data.city || bestMatch.data.settlement, // Добавляем логирование поселка
          settlement: bestMatch.data.settlement
        });
      }
    } catch(e) { 
      console.error('DaData address error', e); 
    }
  };

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // Обработка изменения типа доставки
    if (name === 'deliveryType') {
      const newDeliveryType = value;
      const previousType = deliveryType;
      
      console.log('Изменение типа доставки:', { 
        с: previousType, 
        на: newDeliveryType, 
        hasPickupPoint: !!selectedPickupPoint 
      });
      
      // Проверяем, не выбран ли недоступный тип доставки
      if (disabledDeliveryTypes.includes(newDeliveryType)) {
        console.log(`Тип доставки ${newDeliveryType} недоступен`);
        setDeliveryError(`Курьерская доставка невозможна по указанному адресу. Пожалуйста, выберите другой способ доставки или измените адрес.`);
        return;
      }
      
      // Установка нового типа доставки
      setDeliveryType(newDeliveryType);
      
      // Обработка переключения между типами доставки
      if (newDeliveryType === 'boxberry_pickup_point') {
        // Включаем флаг BoxBerry доставки при выборе ПВЗ
        setIsBoxberryDelivery(true);
      } else {
        // Отключаем флаг BoxBerry доставки
        setIsBoxberryDelivery(false);
        
        // Если переключаемся с ПВЗ на другой тип, очищаем выбранный пункт выдачи
        if (selectedPickupPoint) {
          console.log('Сброс выбранного пункта выдачи');
          setSelectedPickupPoint(null);
          setFormData(prev => ({...prev, delivery_address: ''}));
        }
      }
      
      // Если переключаемся на что-то кроме курьерской доставки BoxBerry,
      // сбрасываем данные адреса
      if (newDeliveryType !== 'boxberry_courier') {
        console.log('Сброс данных адреса при переключении с курьерской доставки');
        setSelectedAddressData(null);
      }
      
      // Сбрасываем стоимость доставки и период доставки при смене типа
      setDeliveryCost(0);
      setDeliveryPeriod(0);
      setDeliveryError(null);
      return;
    }
    
    // Обработка изменения способа оплаты
    if (name === 'paymentMethod') {
      const newPaymentOnDelivery = value === 'on_delivery';
      // Вызываем расчет только если значение меняется
      if (isPaymentOnDelivery !== newPaymentOnDelivery) {
        calculateDeliveryCost(newPaymentOnDelivery);
        setIsPaymentOnDelivery(newPaymentOnDelivery);
      }
      return;
    }
    
    // Если включается BoxBerry, сбрасываем адрес доставки
    if (name === 'isBoxberryDelivery') {
      setIsBoxberryDelivery(checked);
      if (checked) {
        // Если у нас уже был выбран пункт, восстанавливаем его
        if (selectedPickupPoint) {
          setFormData(prev => ({
            ...prev, 
            delivery_address: selectedPickupPoint.Address
          }));
        } else {
          // Иначе очищаем поле адреса
          setFormData(prev => ({...prev, delivery_address: ''}));
        }
      }
      return;
    }
    
    if (name === 'fullName') { 
      fetchNameSuggestions(value); 
      setFormData(prev => ({...prev, fullName: value})); 
      return; 
    }
    
    if (name === 'delivery_address') {
      // Если активирована доставка BoxBerry, не разрешаем менять поле адреса
      if (isBoxberryDelivery) return;
      
      const newValue = value;
      fetchAddressSuggestions(newValue);
      setFormData(prev => ({...prev, delivery_address: newValue}));
      
      // При существенном изменении адреса сбрасываем недоступные типы доставки
      if (selectedAddressData && selectedAddressData.postal_code) {
        const currentAddressStart = selectedAddressData.value.substring(0, Math.min(selectedAddressData.value.length, 10));
        const newAddressStart = newValue.substring(0, Math.min(newValue.length, 10));
        
        if (!newValue.includes(currentAddressStart) && !currentAddressStart.includes(newAddressStart)) {
          // Если это существенно новый адрес, сбрасываем ограничения доставки
          setDisabledDeliveryTypes([]);
          setDeliveryError(null);
        }
      }
      
      // Для курьерской доставки BoxBerry сбрасываем данные адреса 
      // только если новый ввод радикально отличается от текущего
      if (deliveryType === 'boxberry_courier' && selectedAddressData) {
        // Проверяем, что новый адрес не является уточнением уже выбранного
        // Например, человек мог выбрать "ул. Ленина" и дописывает номер дома
        const currentAddressStart = selectedAddressData.value.substring(0, Math.min(selectedAddressData.value.length, 10));
        const newAddressStart = newValue.substring(0, Math.min(newValue.length, 10));
        
        if (!newValue.includes(currentAddressStart) && !currentAddressStart.includes(newAddressStart)) {
          // Если это совершенно другой адрес, сбрасываем данные
          console.log('Сброс данных адреса из-за существенного изменения ввода');
          setSelectedAddressData(null);
        }
      }
      
      // Применяем debounce для расчета доставки при вводе адреса
      if (deliveryType === 'boxberry_courier') {
        debouncedCalculateDelivery(newValue);
      }
      
      return;
    }
    
    if (type === 'checkbox') { 
      setFormData(prev => ({...prev, [name]: checked})); 
      return; 
    }
    
    setFormData(prev => ({...prev, [name]: value}));
  };

  // Обработчик выбора пункта выдачи BoxBerry
  const handlePickupPointSelected = (point) => {
    console.log('Выбран пункт выдачи:', point);
    setSelectedPickupPoint(point);
    // Устанавливаем флаг isBoxberryDelivery в true при выборе пункта
    setIsBoxberryDelivery(true);
    setFormData(prev => ({
      ...prev,
      delivery_address: point.Address
    }));
    
    // Вызываем расчет доставки
    calculateDeliveryCost();
  };

  // Обработчик открытия модального окна BoxBerry
  const handleOpenBoxberryModal = () => {
    setShowBoxberryModal(true);
  };

  // Обработчик применения промокода
  const handlePromoCodeApplied = (promoData) => {
    if (promoData) {
      // Рассчитываем скидку
      let calculatedDiscount = 0;
      if (promoData.discount_percent) {
        calculatedDiscount = Math.floor(cartTotal * promoData.discount_percent / 100);
      } else if (promoData.discount_amount) {
        calculatedDiscount = Math.min(promoData.discount_amount, cartTotal);
      }
      
      setDiscountAmount(calculatedDiscount);
      console.log('Промокод применен:', promoData, 'Скидка:', calculatedDiscount);
    } else {
      setDiscountAmount(0);
      console.log('Промокод удален');
    }
  };
  
  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Валидация формы
    const form = e.currentTarget;
    setValidated(true);
    
    if (!form.checkValidity()) {
      e.stopPropagation();
      return;
    }
    
    // Проверяем, что выбран тип доставки
    if (!deliveryType) {
      setError('Пожалуйста, выберите способ доставки');
      return;
    }
    
    // Проверяем, что для пунктов выдачи указан адрес
    if (deliveryType === 'boxberry_pickup_point' && !selectedPickupPoint) {
      setError('Пожалуйста, выберите пункт выдачи BoxBerry');
      return;
    }
    
    // Проверяем, не является ли выбранный тип доставки недоступным
    if (disabledDeliveryTypes.includes(deliveryType)) {
      setError(`Курьерская доставка невозможна по указанному адресу. Пожалуйста, выберите другой способ доставки.`);
      return;
    }
    
    try {
      // Формируем данные для создания заказа
      const orderData = {
        items: cart.items.map(item => ({
          product_id: item.product.id,
          quantity: item.quantity
        })),
        
        // Данные покупателя
        full_name: formData.fullName,
        email: formData.email,
        phone: formData.phone,
        delivery_address: formData.delivery_address,
        comment: formData.comment,
        
        // Информация о доставке в объекте delivery_info
        delivery_info: {
          delivery_type: deliveryType,
          delivery_cost: deliveryCost,
          boxberry_point_id: (deliveryType === 'boxberry_pickup_point' && selectedPickupPoint) ? parseInt(selectedPickupPoint.Code) : null,
          boxberry_point_address: (deliveryType === 'boxberry_pickup_point' && selectedPickupPoint) ? selectedPickupPoint.Address : null,
          tracking_number: null
        },
        
        // Информация о способе оплаты
        is_payment_on_delivery: isPaymentOnDelivery,
        
        // Промокод (если применен)
        promo_code: promoCode ? promoCode.code : null,
        
        // Соглашения
        personal_data_agreement: formData.personalDataAgreement,
        receive_notifications: formData.receiveNotifications
      };
      
      console.log('Отправка данных заказа:', orderData);
      console.log('Ключи объекта orderData:', Object.keys(orderData));
      console.log('Стоимость доставки (deliveryCost):', deliveryCost);
      console.log('Стоимость доставки в объекте (orderData.delivery_cost):', orderData.delivery_cost);
      
      // Создаем заказ через контекст заказов
      const response = await createOrder(orderData);
      
      if (response) {
        console.log('Заказ успешно создан:', response);
        
        // Создаем номер заказа в формате "ID-ГОД"
        let orderYear;
        if (response.created_at) {
          orderYear = new Date(response.created_at).getFullYear();
        } else {
          orderYear = new Date().getFullYear();
        }
        const formattedOrderNumber = `${response.id}-${orderYear}`;
        
        // Устанавливаем состояние успешного создания заказа
        setOrderSuccess(true);
        setOrderNumber(formattedOrderNumber);
        
        // Очищаем корзину и промокод
        clearCart();
        clearPromoCode();
        
        // Устанавливаем таймер для редиректа на страницу заказов
        const timer = setTimeout(() => {
          navigate('/orders');
        }, 5000);
        
        setRedirectTimer(timer);
      }
    } catch (err) {
      console.error('Ошибка при создании заказа:', err);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(`Ошибка при создании заказа: ${err.response.data.detail}`);
      } else {
        setError('Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте снова.');
      }
    }
  };
  
  // Если заказ успешно создан, показываем сообщение об успехе
  if (orderSuccess) {
    return (
      <div className="checkout-success-container">
        <Card className="checkout-success-card">
          <Card.Body className="text-center">
            <div className="success-icon">✓</div>
            <h2>Заказ успешно оформлен!</h2>
            <p>Ваш номер заказа: <strong>{orderNumber}</strong></p>
            <p>Мы отправили подтверждение на вашу электронную почту.</p>
            <p>Вы будете перенаправлены на страницу заказов через 15 секунд...</p>
            <Button 
              variant="primary" 
              onClick={() => {
                // Отменяем таймер автоматического редиректа
                if (redirectTimer) {
                  clearTimeout(redirectTimer);
                }
                // Проверяем, пуста ли корзина, и если нет - очищаем
                if (cart && cart.items && cart.items.length > 0) {
                  console.log("Корзина до сих пор не пуста, очищаем перед редиректом");
                  clearCart();
                }
                clearPromoCode(); // Очищаем промокод при переходе на страницу заказов
                navigate('/orders');
              }}
              className="mt-3"
            >
              Перейти к заказам
            </Button>
          </Card.Body>
        </Card>
      </div>
    );
  }

  // Основной рендер страницы оформления заказа
  return (
    <div className="checkout-container">
      <h1 className="checkout-title">Оформление заказа</h1>
      
      {error && (
        <Alert variant="danger">
          {error}
        </Alert>
      )}
      
      <Row className="align-items-start">
        {/* Форма оформления заказа */}
        <Col md={8}>
          <Card className="checkout-card">
            <Card.Header>
              <h3 className="checkout-summary-title">Информация о доставке</h3>
            </Card.Header>
            <Card.Body>
              <Form noValidate validated={validated} onSubmit={handleSubmit}>
                <Form.Group controlId="fullName" className="position-relative">
                  <Form.Label>ФИО получателя</Form.Label>
                  <Form.Control
                    type="text"
                    name="fullName"
                    autoComplete="off"
                    value={formData.fullName}
                    onChange={handleChange}
                    required
                  />
                  {nameSuggestions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {nameSuggestions.map((s, i) => (
                        <div
                          key={i}
                          className="suggestion-item px-2 py-1 hover-bg-light"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, fullName: s }));
                            setNameSuggestions([]);
                          }}
                        >
                          {s}
                        </div>
                      ))}
                    </div>
                  )}
                </Form.Group>
                
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Email</Form.Label>
                      <Form.Control
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        required
                        placeholder="example@mail.ru"
                      />
                      <Form.Control.Feedback type="invalid">
                        Пожалуйста, введите корректный email
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Телефон</Form.Label>
                      <Form.Control
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        required
                        placeholder="+7XXXXXXXXXX или 8XXXXXXXXXX"
                        pattern="^(\+7|8)\d{10}$"
                      />
                      <Form.Control.Feedback type="invalid">
                        Пожалуйста, введите корректный номер телефона (начинается с +7 или 8)
                      </Form.Control.Feedback>
                      <Form.Text className="text-muted">
                        Формат: +79999999999 или 89999999999
                      </Form.Text>
                    </Form.Group>
                  </Col>
                </Row>
                
                {/* В форме заказа добавим радиокнопки для выбора доставки */}
                <div className="delivery-options-container">
                  <div className="delivery-options-title">Способ доставки<span className="text-danger">*</span></div>
                  
                  <div className={`delivery-option ${deliveryType === 'boxberry_courier' ? 'selected' : ''}`} 
                    onClick={() => {
                      // Проверяем, не является ли тип доставки недоступным
                      if (disabledDeliveryTypes.includes('boxberry_courier')) {
                        return;
                      }
                      
                      // При клике на контейнер используем handleChange с синтетическим event объектом
                      handleChange({
                        target: {
                          name: 'deliveryType',
                          value: 'boxberry_courier'
                        }
                      });
                    }}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="boxberry_courier"
                      value="boxberry_courier"
                      checked={deliveryType === 'boxberry_courier'}
                      onChange={handleChange}
                      disabled={disabledDeliveryTypes.includes('boxberry_courier')}
                      required
                    />
                    <label className="form-check-label" htmlFor="boxberry_courier">
                      Курьер BoxBerry
                      {disabledDeliveryTypes.includes('boxberry_courier') && (
                        <span className="text-danger ms-2">(недоступно для указанного адреса)</span>
                      )}
                    </label>
                  </div>
                  
                  <div className={`delivery-option ${deliveryType === 'boxberry_pickup_point' ? 'selected' : ''}`}
                    onClick={() => {
                      // При клике на контейнер используем handleChange с синтетическим event объектом
                      handleChange({
                        target: {
                          name: 'deliveryType',
                          value: 'boxberry_pickup_point'
                        }
                      });
                    }}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="boxberry_pickup_point"
                      value="boxberry_pickup_point"
                      checked={deliveryType === 'boxberry_pickup_point'}
                      onChange={handleChange}
                      required
                    />
                    <label className="form-check-label" htmlFor="boxberry_pickup_point">
                      Пункт выдачи BoxBerry
                    </label>
                  </div>
                  
                  <div className={`delivery-option ${deliveryType === 'cdek_courier' ? 'selected' : ''}`}
                    onClick={() => {
                      // При клике на контейнер используем handleChange с синтетическим event объектом
                      handleChange({
                        target: {
                          name: 'deliveryType',
                          value: 'cdek_courier'
                        }
                      });
                    }}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="cdek_courier"
                      value="cdek_courier"
                      checked={deliveryType === 'cdek_courier'}
                      onChange={handleChange}
                      required
                    />
                    <label className="form-check-label" htmlFor="cdek_courier">
                      Курьер СДЭК
                    </label>
                  </div>
                  
                  <div className={`delivery-option ${deliveryType === 'cdek_pickup_point' ? 'selected' : ''}`}
                    onClick={() => {
                      // При клике на контейнер используем handleChange с синтетическим event объектом
                      handleChange({
                        target: {
                          name: 'deliveryType',
                          value: 'cdek_pickup_point'
                        }
                      });
                    }}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="cdek_pickup_point"
                      value="cdek_pickup_point"
                      checked={deliveryType === 'cdek_pickup_point'}
                      onChange={handleChange}
                      required
                    />
                    <label className="form-check-label" htmlFor="cdek_pickup_point">
                      Пункт выдачи СДЭК
                    </label>
                  </div>
                  
                  {deliveryType === '' && validated && (
                    <div className="delivery-error">
                      Пожалуйста, выберите способ доставки
                    </div>
                  )}
                </div>
                
                {/* Опция выбора доставки в пункт выдачи BoxBerry */}
                {isBoxberryDelivery && (
                  <div className="mb-3">
                    <Button 
                      variant="outline-primary" 
                      onClick={handleOpenBoxberryModal}
                      className="d-block w-100"
                    >
                      {selectedPickupPoint ? "Изменить пункт выдачи" : "Выбрать пункт выдачи BoxBerry"}
                    </Button>
                    {selectedPickupPoint ? (
                      <div className="mt-2 p-2 border rounded bg-light">
                        <p className="mb-1"><strong>{selectedPickupPoint.Name}</strong></p>
                        <p className="mb-1 small">{selectedPickupPoint.Address}</p>
                        <p className="mb-0 small text-muted">График работы: {selectedPickupPoint.WorkShedule}</p>
                      </div>
                    ) : (
                      <div className="mt-2 text-danger">
                        <small>Выберите пункт выдачи для расчета стоимости доставки</small>
                      </div>
                    )}
                  </div>
                )}
                
                <div className="payment-options-container mb-4">
                  <div className="payment-options-title">Способ оплаты<span className="text-danger">*</span></div>
                  
                  <div className={`payment-option ${isPaymentOnDelivery ? 'selected' : ''}`}
                    onClick={() => {
                      if (!isPaymentOnDelivery) {
                        // Вызываем перерасчет доставки с точным значением только если значение меняется
                        calculateDeliveryCost(true);
                        // После расчета делаем setState
                        setIsPaymentOnDelivery(true);
                      }
                    }}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="paymentMethod"
                      id="payment_on_delivery"
                      checked={isPaymentOnDelivery}
                      onChange={(e) => {
                        // onChange срабатывает только при изменении через элемент формы
                        // избегаем вызова здесь, так как onClick на родителе уже делает необходимые действия
                      }}
                      required
                    />
                    <label className="form-check-label" htmlFor="payment_on_delivery">
                      Оплата при получении
                    </label>
                  </div>
                  
                  <div className={`payment-option ${!isPaymentOnDelivery ? 'selected' : ''}`}
                    onClick={() => {
                      if (isPaymentOnDelivery) {
                        // Вызываем перерасчет доставки с точным значением только если значение меняется
                        calculateDeliveryCost(false);
                        // После расчета делаем setState 
                        setIsPaymentOnDelivery(false);
                      }
                    }}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="paymentMethod"
                      id="payment_on_site"
                      checked={!isPaymentOnDelivery}
                      onChange={(e) => {
                        // onChange срабатывает только при изменении через элемент формы
                        // избегаем вызова здесь, так как onClick на родителе уже делает необходимые действия
                      }}
                      required
                    />
                    <label className="form-check-label" htmlFor="payment_on_site">
                      Оплата на сайте
                    </label>
                  </div>
                </div>
                
                <Form.Group className="position-relative" controlId="delivery_address">
                  <Form.Label>Адрес доставки</Form.Label>
                  <Form.Control
                    type="text"
                    name="delivery_address"
                    autoComplete="off"
                    value={formData.delivery_address}
                    onChange={handleChange}
                    required
                    placeholder="Введите полный адрес"
                    disabled={isBoxberryDelivery}
                  />
                  {!isBoxberryDelivery && addressOptions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {addressOptions.map((opt, i) => (
                        <div
                          key={i}
                          className="suggestion-item hover-bg-light"
                          onClick={() => {
                            // Сохраняем полные данные о выбранном адресе для расчета доставки
                            setSelectedAddressData({
                              value: opt.value,
                              postal_code: opt.data.postal_code,
                              city: opt.data.city || opt.data.settlement, // Используем название поселка, если город не указан
                              settlement: opt.data.settlement,
                              street: opt.data.street,
                              house: opt.data.house
                            });
                            
                            setFormData(prev => ({ ...prev, delivery_address: opt.value }));
                            setAddressOptions([]);
                            
                            // Если это курьерская доставка Boxberry, запускаем расчет
                            if (deliveryType === 'boxberry_courier') {
                              calculateDeliveryCost();
                            }
                          }}
                        >
                          {opt.value}
                        </div>
                      ))}
                    </div>
                  )}
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Комментарий к заказу</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    name="comment"
                    value={formData.comment}
                    onChange={handleChange}
                    placeholder="Комментарий к заказу (например, удобное время доставки)"
                  />
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Check
                    required
                    type="checkbox"
                    id="personalDataAgreement"
                    name="personalDataAgreement"
                    checked={formData.personalDataAgreement}
                    onChange={handleChange}
                    label="Я согласен на обработку персональных данных"
                    feedback="Необходимо согласие на обработку персональных данных"
                    feedbackType="invalid"
                  />
                </Form.Group>
                
                {/* Опция подписки на уведомления для незарегистрированных пользователей */}
                {!user && (
                  <Form.Group className="mb-3">
                    <Form.Check
                      type="checkbox"
                      id="receiveNotifications"
                      name="receiveNotifications"
                      checked={formData.receiveNotifications}
                      onChange={handleChange}
                      label="Я хочу получать уведомления о статусе заказа по email"
                    />
                  </Form.Group>
                )}
                
                <Button 
                  variant="primary" 
                  type="submit" 
                  className="w-100"
                  disabled={loading || (isBoxberryDelivery && !selectedPickupPoint)}
                >
                  {loading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                      />
                      <span className="ms-2">Оформление заказа...</span>
                    </>
                  ) : (
                    "Оформить заказ"
                  )}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Информация о заказе */}
        <Col md={4}>
          <Card className="checkout-summary-card">
            <Card.Header>
              <h3 className="checkout-summary-title">Ваш заказ</h3>
            </Card.Header>
            <Card.Body>
              {cart && cart.items && cart.items.length > 0 ? (
                <div className="checkout-summary">
                  <div className="checkout-items">
                    {cart.items.map((item, idx) => (
                      <div key={item.id !== undefined ? item.id : `anon_${item.product_id}_${idx}`} className="checkout-item">
                        <div className="item-name">{item.product.name}</div>
                        <div className="item-quantity">{item.quantity} x {formatPrice(item.product.price)} ₽</div>
                        <div className="item-total">{formatPrice(item.quantity * item.product.price)} ₽</div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Форма промокода */}
                  <PromoCodeForm 
                    email={formData.email} 
                    phone={formData.phone} 
                    cartTotal={cartTotal}
                    onPromoCodeApplied={handlePromoCodeApplied}
                  />
                  
                  <div className="checkout-total">
                    {discountAmount > 0 && (
                      <div className="discount">
                        <div>Скидка:</div>
                        <div>-{formatPrice(discountAmount)} ₽</div>
                      </div>
                    )}
                    
                    {/* Стоимость доставки */}
                    <div className="delivery-cost">
                      <div>Доставка:</div>
                      <div className="delivery-cost-value">
                        {!deliveryType ? (
                          "0 ₽"
                        ) : calculatingDelivery ? (
                          <Spinner animation="border" size="sm" />
                        ) : deliveryError ? (
                          <span className="text-danger">Не удалось рассчитать</span>
                        ) : (
                          `${formatPrice(deliveryCost)} ₽`
                        )}
                      </div>
                    </div>
                    
                    {/* Срок доставки в днях */}
                    {deliveryType && !calculatingDelivery && !deliveryError && deliveryPeriod > 0 && (
                      <div className="delivery-period">
                        <div>Срок доставки:</div>
                        <div>{deliveryPeriod} {getDeliveryPeriodText(deliveryPeriod)}</div>
                      </div>
                    )}
                    
                    <div className="total">
                      <div>Итого:</div>
                      <div>
                        {discountAmount > 0 && (
                          <span className="old-price">{formatPrice(cartTotal)} ₽</span>
                        )}
                        <strong className={discountAmount > 0 ? "new-price" : ""}>
                          {formatPrice(finalTotal)} ₽
                        </strong>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-cart-message">
                  Корзина пуста
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Модальное окно выбора пункта выдачи BoxBerry */}
      <BoxberryPickupModal
        show={showBoxberryModal}
        onHide={() => setShowBoxberryModal(false)}
        onPickupPointSelected={handlePickupPointSelected}
        selectedAddress=""
      />
    </div>
  );
};

export default CheckoutPage; 