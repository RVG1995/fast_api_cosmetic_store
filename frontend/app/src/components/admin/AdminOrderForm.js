import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Form, Button, Container, Row, Col, Card, Alert, Spinner } from 'react-bootstrap';
import { adminAPI } from '../../utils/api';
import { useOrders } from '../../context/OrderContext';
import { debounce } from 'lodash';
import { formatPrice } from '../../utils/helpers';
import { API_URLS } from '../../utils/constants';
import axios from 'axios';
import BoxberryPickupModal from '../cart/BoxberryPickupModal';
import './AdminOrderForm.css';
import { deliveryAPI } from '../../utils/api';

const AdminOrderForm = ({ onClose, onSuccess }) => {
  // Состояние формы
  const [formData, setFormData] = useState({
    user_id: null,
    full_name: '',
    email: '',
    phone: '',
    delivery_address: '',
    comment: '',
    promo_code: '',
    status_id: 1, // По умолчанию первый статус (обычно "Новый")
    is_paid: false,
    delivery_type: '', // Убираем значение по умолчанию
    is_payment_on_delivery: true, // По умолчанию - оплата при получении
    items: []
  });

  // Состояние для списка пользователей
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  
  // Состояние для продуктов
  const [products, setProducts] = useState([]);
  const [searchProduct, setSearchProduct] = useState('');
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  
  // Состояние формы
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Состояние для промокода
  const [promoCodeLoading, setPromoCodeLoading] = useState(false);
  const [promoCodeError, setPromoCodeError] = useState(null);
  const [appliedPromoCode, setAppliedPromoCode] = useState(null);
  const [orderTotal, setOrderTotal] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);
  
  // Состояния для BoxBerry и DaData
  const [showBoxberryModal, setShowBoxberryModal] = useState(false);
  const [addressOptions, setAddressOptions] = useState([]);
  const [selectedPickupPoint, setSelectedPickupPoint] = useState(null);
  
  // Состояния для доставки
  const [deliveryCost, setDeliveryCost] = useState(0);
  const [calculatingDelivery, setCalculatingDelivery] = useState(false);
  const [deliveryError, setDeliveryError] = useState(null);
  const [deliveryPeriod, setDeliveryPeriod] = useState(0);
  
  // Состояние для хранения данных выбранного адреса (postal_code, city и т.д.)
  const [selectedAddressData, setSelectedAddressData] = useState(null);

  // Получаем методы из контекста заказов
  const { getOrderStatuses, createAdminOrder, checkPromoCode, calculateDiscount } = useOrders();

  // Загрузка статусов заказа
  useEffect(() => {
    const loadStatuses = async () => {
      try {
        const data = await getOrderStatuses();
        setStatuses(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Ошибка при загрузке статусов заказов:', err);
        setError('Не удалось загрузить статусы заказов');
      }
    };
    
    loadStatuses();
  }, [getOrderStatuses]);

  // Загрузка списка пользователей
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoadingUsers(true);
        const response = await adminAPI.getAllUsers();
        setUsers(response.data || []);
      } catch (err) {
        console.error('Ошибка при загрузке пользователей:', err);
        setError('Не удалось загрузить список пользователей');
      } finally {
        setLoadingUsers(false);
      }
    };
    
    fetchUsers();
  }, []);

  // Обработчик поиска пользователя с debounce
  const handleUserSearch = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    if (value.length > 1) {
      debouncedSearch(value);
    } else {
      setSearchResults([]);
    }
  };

  // Создаем функцию поиска с debounce
  const debouncedSearch = useCallback(
    debounce((term) => {
      const results = users.filter(user => {
        const fullName = `${user.first_name} ${user.last_name}`.toLowerCase();
        return fullName.includes(term.toLowerCase()) || 
               user.email.toLowerCase().includes(term.toLowerCase());
      });
      setSearchResults(results);
    }, 300),
    [users]
  );

  // Обработчик выбора пользователя
  const handleSelectUser = (user) => {
    setFormData({
      ...formData,
      user_id: user.id,
      full_name: `${user.first_name} ${user.last_name}`,
      email: user.email
    });
    setSearchTerm(`${user.first_name} ${user.last_name}`);
    setSearchResults([]);
  };

  // Обработчик очистки выбранного пользователя
  const handleClearUser = () => {
    setFormData({
      ...formData,
      user_id: null,
      full_name: '',
      email: ''
    });
    setSearchTerm('');
  };

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // Проверяем, изменился ли флаг оплаты при получении
    if (name === 'is_payment_on_delivery' && formData.delivery_type) {
      // Если изменился флаг оплаты, сначала запускаем расчет с точным значением
      calculateDeliveryCost(checked);
      // Затем обновляем состояние
      setFormData({
        ...formData,
        [name]: checked
      });
    } else {
      // Для других полей просто обновляем состояние
      setFormData({
        ...formData,
        [name]: type === 'checkbox' ? checked : value
      });
    }
  };

  // Функция для поиска продуктов
  const searchProducts = async (term) => {
    if (!term || term.length < 2) return;
    
    try {
      setLoadingProducts(true);
      const response = await axios.get(`${API_URLS.PRODUCT_SERVICE}/products/search`, {
        params: { name: term },
        withCredentials: true
      });
      setProducts(response.data || []);
    } catch (err) {
      console.error('Ошибка при поиске продуктов:', err);
    } finally {
      setLoadingProducts(false);
    }
  };

  // Функция с debounce для поиска продуктов
  const debouncedProductSearch = useCallback(
    debounce((term) => searchProducts(term), 300),
    []
  );

  // Обработчик изменения поля поиска продукта
  const handleProductSearch = (e) => {
    const value = e.target.value;
    setSearchProduct(value);
    debouncedProductSearch(value);
  };

  // Обработчик выбора продукта
  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setSearchProduct('');
    setProducts([]);
  };

  // Обработчик добавления продукта к заказу
  const handleAddProduct = () => {
    if (!selectedProduct) return;
    
    // Проверяем, есть ли уже этот товар в списке
    const existingItemIndex = formData.items.findIndex(
      item => item.product_id === selectedProduct.id
    );
    
    if (existingItemIndex !== -1) {
      // Если товар уже есть, увеличиваем количество
      const newItems = [...formData.items];
      newItems[existingItemIndex].quantity += parseInt(quantity, 10);
      
      setFormData({
        ...formData,
        items: newItems
      });
    } else {
      // Если товара нет, добавляем новый
      setFormData({
        ...formData,
        items: [
          ...formData.items,
          {
            product_id: selectedProduct.id,
            quantity: parseInt(quantity, 10),
            product_name: selectedProduct.name,
            price: selectedProduct.price
          }
        ]
      });
    }
    
    setSelectedProduct(null);
    setQuantity(1);
  };

  // Обработчик изменения количества товара
  const handleQuantityChange = (index, newQuantity) => {
    // Проверяем, что количество положительное
    if (newQuantity < 1) newQuantity = 1;
    
    const newItems = [...formData.items];
    newItems[index].quantity = parseInt(newQuantity, 10);
    
    setFormData({
      ...formData,
      items: newItems
    });
  };

  // Обработчик удаления продукта из заказа
  const handleRemoveProduct = (index) => {
    const newItems = [...formData.items];
    newItems.splice(index, 1);
    setFormData({
      ...formData,
      items: newItems
    });
  };

  // Вычисляем общую сумму заказа
  const totalPrice = useMemo(() => {
    return formData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }, [formData.items]);

  // Рассчитываем итоговую сумму заказа при изменении товаров
  useEffect(() => {
    const total = formData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    setOrderTotal(total);
    
    // Перерасчет скидки, если применен промокод
    if (appliedPromoCode) {
      let discount = 0;
      if (appliedPromoCode.discountPercent) {
        discount = Math.floor(total * appliedPromoCode.discountPercent / 100);
      } else if (appliedPromoCode.discountAmount) {
        discount = Math.min(appliedPromoCode.discountAmount, total);
      }
      setDiscountAmount(discount);
    }
  }, [formData.items, appliedPromoCode]);

  // Обработчик проверки промокода
  const handleCheckPromoCode = async () => {
    if (!formData.promo_code || formData.promo_code.trim() === '') {
      setPromoCodeError('Введите промокод');
      return;
    }
    
    if (!formData.email || !formData.email.includes('@')) {
      setPromoCodeError('Введите корректный email для проверки промокода');
      return;
    }
    
    // Проверка на наличие товаров в заказе
    if (formData.items.length === 0) {
      setPromoCodeError('Добавьте хотя бы один товар перед применением промокода');
      return;
    }
    
    try {
      setPromoCodeLoading(true);
      setPromoCodeError(null);
      
      // Проверка телефона для API
      let phone = formData.phone || '';
      if (phone && !phone.startsWith('8') && !phone.startsWith('+7')) {
        phone = '8' + phone;
      }
      
      // Если телефон пустой или слишком короткий, используем дефолтное значение
      if (!phone || phone.length < 11) {
        phone = '80000000000';
      }
      
      const result = await checkPromoCode(formData.promo_code, formData.email, phone);
      
      if (result && result.is_valid) {
        const promoData = {
          code: formData.promo_code,
          discountPercent: result.discount_percent,
          discountAmount: result.discount_amount,
          promoCodeId: result.promo_code?.id
        };
        
        setAppliedPromoCode(promoData);
        
        // Рассчитываем скидку
        let discount = 0;
        if (result.discount_percent) {
          discount = Math.floor(orderTotal * result.discount_percent / 100);
        } else if (result.discount_amount) {
          discount = Math.min(result.discount_amount, orderTotal);
        }
        
        setDiscountAmount(discount);
      } else {
        setPromoCodeError('Недействительный промокод');
        setAppliedPromoCode(null);
        setDiscountAmount(0);
      }
    } catch (err) {
      console.error('Ошибка при проверке промокода:', err);
      setPromoCodeError('Ошибка при проверке промокода');
      setAppliedPromoCode(null);
      setDiscountAmount(0);
    } finally {
      setPromoCodeLoading(false);
    }
  };

  // Обработчик удаления промокода
  const handleRemovePromoCode = () => {
    setFormData({
      ...formData,
      promo_code: ''
    });
    setAppliedPromoCode(null);
    setDiscountAmount(0);
    setPromoCodeError(null);
  };

  // Вычисляем итоговую стоимость с учетом скидки
  const finalTotal = Math.max(0, orderTotal - discountAmount);

  // Подсказки адресов DaData
  const fetchAddressSuggestions = async (query) => {
    if (!query || query.trim().length < 3) {
      setAddressOptions([]);
      return;
    }
    
    try {
      const { data } = await axios.post(
        `${API_URLS.DELIVERY_SERVICE}/delivery/dadata/address`,
        { query }
      );
      
      const suggestions = data.suggestions || [];
      setAddressOptions(suggestions);
      
      // Если есть результаты и выбрана курьерская доставка BoxBerry, 
      // используем первый (наиболее релевантный) результат автоматически
      if (suggestions.length > 0 && formData.delivery_type === 'boxberry_courier') {
        const bestMatch = suggestions[0];
        
        // Автоматически устанавливаем данные адреса из лучшего совпадения
        setSelectedAddressData({
          value: bestMatch.value,
          postal_code: bestMatch.data.postal_code,
          city: bestMatch.data.city,
          street: bestMatch.data.street,
          house: bestMatch.data.house
        });
        
        console.log('Автоматически выбраны данные адреса:', {
          value: bestMatch.value,
          postal_code: bestMatch.data.postal_code,
          city: bestMatch.data.city
        });
      }
    } catch(e) { 
      console.error('DaData address error', e); 
      setAddressOptions([]);
    }
  };

  // Debounce для поиска адресов
  const debouncedAddressSearch = useCallback(
    debounce((query) => fetchAddressSuggestions(query), 300),
    []
  );

  // Обработчик выбора адреса из подсказок
  const handleSelectAddress = (address) => {
    setFormData({
      ...formData,
      delivery_address: address.value
    });
    
    // Сохраняем данные адреса для расчета курьерской доставки
    setSelectedAddressData({
      value: address.value,
      postal_code: address.data.postal_code,
      city: address.data.city,
      street: address.data.street,
      house: address.data.house
    });
    
    console.log('Выбран адрес с данными:', {
      postal_code: address.data.postal_code,
      city: address.data.city
    });
    
    setAddressOptions([]);
  };

  // Обработчик изменения адреса
  const handleAddressChange = (e) => {
    const value = e.target.value;
    setFormData({
      ...formData,
      delivery_address: value
    });
    
    if (value.length >= 3) {
      debouncedAddressSearch(value);
      
      // Если выбрана курьерская доставка BoxBerry, делаем отложенный расчет доставки
      if (formData.delivery_type === 'boxberry_courier') {
        debouncedCalculateDelivery(value);
      }
    } else {
      setAddressOptions([]);
    }
  };
  
  // Функция для отложенного выполнения расчета доставки
  const debouncedCalculateDelivery = useCallback(
    (() => {
      let timer = null;
      return (address) => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
          if (address && address.length > 5 && formData.delivery_type === 'boxberry_courier') {
            calculateDeliveryCost();
          }
        }, 1000); // Задержка в 1 секунду
      };
    })(),
    [formData.delivery_type, formData.is_payment_on_delivery, formData.items]
  );

  // Функция для расчета стоимости доставки
  // Позволяет передать явное значение флага is_payment_on_delivery
  const calculateDeliveryCost = async (forcePaymentOnDelivery = null) => {
    // Определяем текущее или переданное значение флага оплаты при получении
    const isPaymentOnDelivery = forcePaymentOnDelivery !== null 
      ? forcePaymentOnDelivery 
      : formData.is_payment_on_delivery;
    
    console.log('Запуск расчета стоимости доставки', {
      delivery_type: formData.delivery_type,
      is_payment_on_delivery: isPaymentOnDelivery,
      state_payment_on_delivery: formData.is_payment_on_delivery,
      force_value: forcePaymentOnDelivery
    });
    
    // Если нет выбранного типа доставки или товаров, не выполняем расчет
    if (!formData.delivery_type || formData.items.length === 0) {
      setDeliveryCost(0);
      setDeliveryPeriod(0);
      return;
    }
    
    // Проверяем наличие необходимых данных для расчета
    if (formData.delivery_type === 'boxberry_pickup_point') {
      // Обязательно нужен выбранный пункт
      if (!selectedPickupPoint) {
        console.log('Не хватает данных для расчета: не выбран пункт выдачи');
        return;
      }
    } else if (formData.delivery_type === 'boxberry_courier') {
      // Для курьерской доставки BoxBerry нужен почтовый индекс
      if (!selectedAddressData || !selectedAddressData.postal_code) {
        console.log('Не хватает данных для расчета курьерской доставки: нет почтового индекса');
        return;
      }
    }
    
    try {
      setCalculatingDelivery(true);
      setDeliveryError(null);
      
      // Формируем предположительные данные о товарах для расчета
      const cartItems = formData.items.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        price: item.price,
        weight: 500, // Используем 500г по умолчанию
        height: 10,  // Используем 10см по умолчанию
        width: 10,   // Используем 10см по умолчанию
        depth: 10    // Используем 10см по умолчанию
      }));
      
      // Данные для отправки на сервер
      const deliveryData = {
        items: cartItems,
        delivery_type: formData.delivery_type,
        is_payment_on_delivery: isPaymentOnDelivery // Используем актуальное значение
      };
      
      // Если выбран пункт выдачи BoxBerry, добавляем его код
      if (formData.delivery_type === 'boxberry_pickup_point' && selectedPickupPoint) {
        deliveryData.pvz_code = selectedPickupPoint.Code;
      }
      
      // Если выбрана курьерская доставка BoxBerry и есть данные адреса
      if (formData.delivery_type === 'boxberry_courier' && selectedAddressData) {
        // Добавляем почтовый индекс, если он есть
        if (selectedAddressData.postal_code) {
          deliveryData.zip_code = selectedAddressData.postal_code;
        }
        
        // Дополнительно можно передать город
        if (selectedAddressData.city) {
          deliveryData.recipient_city = selectedAddressData.city;
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
      setDeliveryError('Не удалось рассчитать стоимость доставки');
      setDeliveryCost(0);
    } finally {
      setCalculatingDelivery(false);
    }
  };

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
  
  // Вызываем расчет стоимости доставки при изменении типа доставки, пункта выдачи или товаров,
  // но НЕ при изменении способа оплаты (это обрабатывается в handleChange)
  useEffect(() => {
    console.log('Изменились параметры для расчета доставки:', { 
      deliveryType: formData.delivery_type, 
      selectedPoint: selectedPickupPoint?.Code,
      itemsCount: formData.items.length
    });
    // Используем текущее значение способа оплаты из formData
    calculateDeliveryCost(); 
  }, [formData.delivery_type, selectedPickupPoint, formData.items]); // Убрали formData.is_payment_on_delivery

  // Обработчик выбора пункта выдачи BoxBerry
  const handlePickupPointSelected = (point) => {
    setSelectedPickupPoint(point);
    
    // Обновляем данные формы с адресом и ID пункта выдачи
    setFormData({
      ...formData,
      delivery_address: point.Address, 
      boxberry_point_id: parseInt(point.Code, 10) // Добавляем ID пункта выдачи как число
    });
    
    console.log(`Выбран пункт выдачи: Code=${point.Code}, Address=${point.Address}`);
    
    // Вызываем расчет доставки
    calculateDeliveryCost();
  };

  // Проверка, является ли выбранный способ доставки пунктом выдачи
  const isPickupPoint = formData.delivery_type.includes('pickup_point');

  // Обработчик изменения типа доставки
  const handleDeliveryTypeChange = (e) => {
    const { value } = e.target;
    const isPickup = value.includes('pickup_point');
    
    // При любом изменении типа доставки сбрасываем предыдущие данные
    if (value !== formData.delivery_type) {
      // Если переключаемся на не-ПВЗ, очищаем выбранный пункт выдачи
      if (!isPickup) {
        setSelectedPickupPoint(null);
        
        // Если был выбран пункт и адрес от него, очищаем адрес
        if (selectedPickupPoint) {
          setFormData(prev => ({
            ...prev,
            delivery_type: value,
            delivery_address: ''
          }));
          return; // Выходим, так как уже обновили formData
        }
      }
      
      // Если выбрана не курьерская доставка BoxBerry, сбрасываем данные адреса
      if (value !== 'boxberry_courier') {
        setSelectedAddressData(null);
      }
      
      // Обнуляем стоимость доставки и период при изменении типа
      setDeliveryCost(0);
      setDeliveryPeriod(0);
      setDeliveryError(null);
    }
    
    setFormData({
      ...formData,
      delivery_type: value
    });
  };

  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.items.length === 0) {
      setError('Заказ должен содержать хотя бы один товар');
      return;
    }
    
    // Проверка заполнения обязательных полей
    if (!formData.full_name || !formData.email || !formData.delivery_address) {
      setError('Пожалуйста, заполните все обязательные поля');
      return;
    }
    
    // Проверка типа доставки
    if (!formData.delivery_type) {
      setError('Пожалуйста, выберите способ доставки');
      return;
    }
    
    // Для пунктов выдачи проверяем, что выбран пункт
    if (formData.delivery_type.includes('pickup_point') && !selectedPickupPoint) {
      setError('Для выбранного способа доставки необходимо выбрать пункт выдачи');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Создаем объект заказа для отправки на сервер
      const orderData = {
        ...formData,
        status_id: parseInt(formData.status_id, 10),
        is_paid: Boolean(formData.is_paid),
        delivery_cost: deliveryCost, // Используем рассчитанную стоимость доставки
        is_payment_on_delivery: Boolean(formData.is_payment_on_delivery)
      };
      
      // Если тип доставки - пункт выдачи, добавляем информацию о пункте выдачи
      if (formData.delivery_type.includes('pickup_point')) {
        // Копируем адрес доставки в поле boxberry_point_address
        orderData.boxberry_point_address = formData.delivery_address;
        
        // Убедимся, что ID пункта выдачи передается как число
        if (selectedPickupPoint) {
          orderData.boxberry_point_id = parseInt(selectedPickupPoint.Code, 10);
          console.log(`Отправка заказа с пунктом выдачи ID=${orderData.boxberry_point_id}`);
        } else if (formData.boxberry_point_id) {
          orderData.boxberry_point_id = parseInt(formData.boxberry_point_id, 10);
          console.log(`Отправка заказа с сохраненным ID пункта выдачи=${orderData.boxberry_point_id}`);
        }
      }
      
      // Обработка телефона
      if (orderData.phone) {
        // Добавляем префикс 8, если его нет
        if (!orderData.phone.startsWith('8') && !orderData.phone.startsWith('+7')) {
          orderData.phone = '8' + orderData.phone;
        }
        
        // Проверяем минимальную длину
        if (orderData.phone.startsWith('8') && orderData.phone.length < 11) {
          const missingDigits = 11 - orderData.phone.length;
          orderData.phone = orderData.phone + '0'.repeat(missingDigits);
        } else if (orderData.phone.startsWith('+7') && orderData.phone.length < 12) {
          const missingDigits = 12 - orderData.phone.length;
          orderData.phone = orderData.phone + '0'.repeat(missingDigits);
        }
      } else {
        // Если телефон пустой, заполняем его дефолтным значением
        orderData.phone = '80000000000';
      }
      
      // Если промокод был проверен и применен, добавляем его ID
      if (appliedPromoCode && appliedPromoCode.promoCodeId) {
        orderData.promo_code_id = appliedPromoCode.promoCodeId;
      } else if (!orderData.promo_code || orderData.promo_code.length < 3) {
        orderData.promo_code = null;
      }
      
      // Отправляем запрос для создания заказа через контекст
      const response = await createAdminOrder(orderData);
      
      setSuccess(true);
      if (onSuccess) onSuccess(response);
    } catch (err) {
      console.error('Ошибка при создании заказа:', err);
      
      // Проверяем, является ли detail массивом ошибок валидации
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Форматируем ошибки в текстовый формат
        const errorMessages = detail.map(item => 
          `${item.loc[item.loc.length - 1]}: ${item.msg}`
        ).join(', ');
        setError(`Ошибка валидации: ${errorMessages}`);
      } else {
        // Если не массив, используем старую логику
        setError(detail || 'Не удалось создать заказ');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container className="my-4">

          {error && <Alert variant="danger">{error}</Alert>}
          {success && <Alert variant="success">Заказ успешно создан!</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <h5 className="mb-3">Информация о получателе</h5>
            <Row className="mb-4">
              <Col md={8}>
                <Form.Group className="mb-3">
                  <Form.Label>Поиск пользователя</Form.Label>
                  <div className="position-relative">
                    <Form.Control
                      type="text"
                      placeholder="Введите имя, фамилию или email пользователя"
                      value={searchTerm}
                      onChange={handleUserSearch}
                    />
                    {loadingUsers && (
                      <div className="position-absolute top-50 end-0 translate-middle-y pe-3">
                        <Spinner animation="border" size="sm" />
                      </div>
                    )}
                    {formData.user_id && (
                      <div className="position-absolute top-50 end-0 translate-middle-y pe-3">
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0 text-danger"
                          onClick={handleClearUser}
                        >
                          ✕
                        </Button>
                      </div>
                    )}
                    {searchResults.length > 0 && !formData.user_id && (
                      <div className="position-absolute start-0 w-100 shadow bg-white rounded z-index-1000" style={{ zIndex: 1000 }}>
                        <ul className="list-group">
                          {searchResults.map(user => (
                            <li
                              key={user.id}
                              className="list-group-item list-group-item-action"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleSelectUser(user)}
                            >
                              {user.first_name} {user.last_name} ({user.email})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  <Form.Text className="text-muted">
                    {formData.user_id 
                      ? `Выбран пользователь с ID: ${formData.user_id}` 
                      : 'Оставьте поле пустым для анонимного заказа'}
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>ФИО получателя*</Form.Label>
                  <Form.Control
                    type="text"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Email*</Form.Label>
                  <Form.Control
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Телефон</Form.Label>
                  <Form.Control
                    type="text"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Промокод</Form.Label>
                  <div className="d-flex">
                    <Form.Control
                      type="text"
                      name="promo_code"
                      value={formData.promo_code}
                      onChange={handleChange}
                      disabled={!!appliedPromoCode}
                    />
                    {!appliedPromoCode ? (
                      <Button 
                        variant="outline-primary" 
                        className="ms-2"
                        onClick={handleCheckPromoCode}
                        disabled={promoCodeLoading}
                      >
                        {promoCodeLoading ? (
                          <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                        ) : (
                          "Проверить"
                        )}
                      </Button>
                    ) : (
                      <Button 
                        variant="outline-danger" 
                        className="ms-2"
                        onClick={handleRemovePromoCode}
                      >
                        Удалить
                      </Button>
                    )}
                  </div>
                  {promoCodeError && (
                    <Form.Text className="text-danger">{promoCodeError}</Form.Text>
                  )}
                  {appliedPromoCode && (
                    <Alert variant="success" className="mt-2 mb-0">
                      <div>
                        <strong>Промокод применен: {appliedPromoCode.code}</strong>
                      </div>
                      <div>
                        {appliedPromoCode.discountPercent ? (
                          <span>Скидка {appliedPromoCode.discountPercent}%</span>
                        ) : (
                          <span>Скидка {formatPrice(appliedPromoCode.discountAmount)} ₽</span>
                        )}
                        {orderTotal > 0 && (
                          <span className="ms-2">({formatPrice(discountAmount)} ₽)</span>
                        )}
                      </div>
                    </Alert>
                  )}
                </Form.Group>
              </Col>
            </Row>
            
            <h5 className="mb-3 mt-4">Адрес доставки</h5>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Способ доставки*</Form.Label>
                  <Form.Select
                    name="delivery_type"
                    value={formData.delivery_type}
                    onChange={handleDeliveryTypeChange}
                    required
                  >
                    <option value="">Выберите способ доставки</option>
                    <option value="boxberry_courier">Курьер Boxberry</option>
                    <option value="boxberry_pickup_point">Пункт выдачи Boxberry</option>
                    <option value="cdek_courier">Курьер СДЭК</option>
                    <option value="cdek_pickup_point">Пункт выдачи СДЭК</option>
                  </Form.Select>
                </Form.Group>
              </Col>

              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Адрес доставки*</Form.Label>
                  <div className="position-relative">
                    <Form.Control
                      type="text"
                      name="delivery_address"
                      value={formData.delivery_address}
                      onChange={handleAddressChange}
                      disabled={isPickupPoint && selectedPickupPoint}
                      required
                    />
                    {addressOptions.length > 0 && (
                      <div className="position-absolute start-0 w-100 shadow bg-white rounded z-index-1000" style={{ zIndex: 1000 }}>
                        <ul className="list-group">
                          {addressOptions.map((address, index) => (
                            <li
                              key={index}
                              className="list-group-item list-group-item-action"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleSelectAddress(address)}
                            >
                              {address.value}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  <Form.Text className="text-muted">
                    {isPickupPoint 
                      ? 'Для пункта выдачи адрес будет заполнен автоматически при выборе пункта' 
                      : 'Укажите адрес доставки для курьера'}
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>
            
            {/* Отображение кнопки выбора пунктов выдачи в отдельном блоке */}
            {isPickupPoint && (
              <Row className="mb-3">
                <Col md={12}>
                  <Button 
                    variant="outline-primary" 
                    onClick={() => setShowBoxberryModal(true)}
                    className="d-block mb-2"
                  >
                    {selectedPickupPoint ? "Изменить пункт выдачи" : "Выбрать пункт выдачи BoxBerry"}
                  </Button>
                  {selectedPickupPoint && (
                    <div className="p-2 border rounded bg-light">
                      <p className="mb-1"><strong>{selectedPickupPoint.Name}</strong></p>
                      <p className="mb-1 small">{selectedPickupPoint.Address}</p>
                      <p className="mb-0 small text-muted">График работы: {selectedPickupPoint.WorkShedule}</p>
                    </div>
                  )}
                </Col>
              </Row>
            )}
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Стоимость доставки</Form.Label>
                  <div className="delivery-cost-display">
                    {!formData.delivery_type ? (
                      <span className="form-control text-muted">0 ₽</span>
                    ) : calculatingDelivery ? (
                      <div className="form-control d-flex align-items-center">
                        <Spinner animation="border" size="sm" className="me-2" />
                        <span>Расчет...</span>
                      </div>
                    ) : deliveryError ? (
                      <span className="form-control text-danger">Не удалось рассчитать</span>
                    ) : (
                      <span className="form-control">{formatPrice(deliveryCost)} ₽</span>
                    )}
                  </div>
                  {formData.delivery_type && !calculatingDelivery && !deliveryError && deliveryPeriod > 0 && (
                    <Form.Text className="text-muted">
                      Срок доставки: {deliveryPeriod} {getDeliveryPeriodText(deliveryPeriod)}
                    </Form.Text>
                  )}
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3 mt-2">
                  <Form.Check
                    type="checkbox"
                    id="is_payment_on_delivery"
                    name="is_payment_on_delivery"
                    label="Оплата при получении"
                    checked={formData.is_payment_on_delivery}
                    onChange={handleChange}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={12}>
                <Form.Group className="mb-3">
                  <Form.Label>Комментарий к заказу</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    name="comment"
                    value={formData.comment}
                    onChange={handleChange}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <h5 className="mb-3 mt-4">Товары</h5>
            <Row className="mb-3">
              <Col md={5}>
                <Form.Group>
                  <Form.Label>Поиск товара</Form.Label>
                  <div className="position-relative">
                    <Form.Control
                      type="text"
                      placeholder="Название товара"
                      value={searchProduct}
                      onChange={handleProductSearch}
                    />
                    {loadingProducts && (
                      <div className="position-absolute top-50 end-0 translate-middle-y pe-3">
                        <Spinner animation="border" size="sm" />
                      </div>
                    )}
                    {products.length > 0 && (
                      <div className="position-absolute start-0 w-100 shadow bg-white rounded" style={{ zIndex: 1000 }}>
                        <ul className="list-group">
                          {products.map(product => (
                            <li
                              key={product.id}
                              className="list-group-item list-group-item-action"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleSelectProduct(product)}
                            >
                              {product.name} - {formatPrice(product.price)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group>
                  <Form.Label>Количество</Form.Label>
                  <Form.Control
                    type="number"
                    min="1"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    disabled={!selectedProduct}
                  />
                </Form.Group>
              </Col>
              <Col md={4} className="d-flex align-items-end">
                <Button 
                  variant="primary" 
                  onClick={handleAddProduct} 
                  disabled={!selectedProduct}
                  className="mb-2"
                >
                  Добавить товар
                </Button>
              </Col>
            </Row>
            
            {selectedProduct && (
              <Alert variant="info" className="mb-3">
                Выбран товар: {selectedProduct.name} - {formatPrice(selectedProduct.price)}
              </Alert>
            )}
            
            {formData.items.length > 0 ? (
              <div className="table-responsive mb-4">
                <table className="table table-striped">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th>Цена</th>
                      <th>Количество</th>
                      <th>Сумма</th>
                      <th>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {formData.items.map((item, index) => (
                      <tr key={index}>
                        <td>{item.product_name}</td>
                        <td>{formatPrice(item.price)}</td>
                        <td>
                          <Form.Control
                            type="number"
                            min="1"
                            value={item.quantity}
                            onChange={(e) => handleQuantityChange(index, e.target.value)}
                            size="sm"
                            style={{ width: '80px' }}
                            className="text-center"
                          />
                        </td>
                        <td>{formatPrice(item.price * item.quantity)}</td>
                        <td>
                          <Button 
                            variant="danger" 
                            size="sm"
                            onClick={() => handleRemoveProduct(index)}
                          >
                            Удалить
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th colSpan="3">Итого товары:</th>
                      <th>
                        {appliedPromoCode && discountAmount > 0 ? (
                          <>
                            <span style={{ textDecoration: 'line-through', color: '#999' }}>
                              {formatPrice(totalPrice)} ₽
                            </span>{' '}
                            <span className="text-success">
                              {formatPrice(totalPrice - discountAmount)} ₽
                            </span>
                          </>
                        ) : (
                          formatPrice(totalPrice)
                        )}
                      </th>
                      <th></th>
                    </tr>
                    {appliedPromoCode && discountAmount > 0 && (
                      <tr>
                        <td colSpan="3" className="text-end text-success">
                          <strong>Скидка по промокоду:</strong>
                        </td>
                        <td className="text-success">
                          <strong>-{formatPrice(discountAmount)} ₽</strong>
                        </td>
                        <td></td>
                      </tr>
                    )}
                    {deliveryCost > 0 && !calculatingDelivery && !deliveryError && (
                      <tr>
                        <td colSpan="3" className="text-end">
                          <strong>Доставка:</strong>
                        </td>
                        <td>
                          <strong>{formatPrice(deliveryCost)} ₽</strong>
                        </td>
                        <td></td>
                      </tr>
                    )}
                    <tr>
                      <td colSpan="3" className="text-end">
                        <strong>Итого к оплате:</strong>
                      </td>
                      <td>
                        <strong>{formatPrice(finalTotal + deliveryCost)} ₽</strong>
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <Alert variant="warning" className="mb-4">
                Добавьте хотя бы один товар в заказ
              </Alert>
            )}
            
            <h5 className="mb-3 mt-4">Статус и оплата</h5>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Статус заказа</Form.Label>
                  <Form.Select
                    name="status_id"
                    value={formData.status_id}
                    onChange={handleChange}
                  >
                    {statuses.map(status => (
                      <option key={status.id} value={status.id}>
                        {status.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3 mt-4">
                  <Form.Check
                    type="checkbox"
                    id="is_paid"
                    name="is_paid"
                    label="Заказ оплачен"
                    checked={formData.is_paid}
                    onChange={handleChange}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <div className="d-flex justify-content-end mt-4">
              <Button variant="secondary" onClick={onClose} className="me-2">
                Отмена
              </Button>
              <Button 
                variant="primary" 
                type="submit" 
                disabled={loading || formData.items.length === 0}
              >
                {loading ? 'Создание заказа...' : 'Создать заказ'}
              </Button>
            </div>
          </Form>

          {/* Модальное окно выбора пункта выдачи BoxBerry */}
          <BoxberryPickupModal
            show={showBoxberryModal}
            onHide={() => setShowBoxberryModal(false)}
            onPickupPointSelected={handlePickupPointSelected}
            selectedAddress={formData.delivery_address}
          />
    </Container>
  );
};

export default AdminOrderForm; 