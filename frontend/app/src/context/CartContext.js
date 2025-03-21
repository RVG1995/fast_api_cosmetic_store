import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { cartAPI } from '../utils/api';
import { useAuth } from './AuthContext';

// Создаем контекст для корзины
const CartContext = createContext();

// Хук для использования контекста корзины
export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart должен использоваться внутри CartProvider');
  }
  return context;
};

// Провайдер контекста корзины
export const CartProvider = ({ children }) => {
  const { user } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cartSummary, setCartSummary] = useState({ total_items: 0, total_price: 0 });

  // Загрузка корзины
  const fetchCart = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await cartAPI.getCart();
      setCart(response.data);
      
      // Обновляем сводку корзины
      setCartSummary({
        total_items: response.data.total_items || 0,
        total_price: response.data.total_price || 0
      });
    } catch (err) {
      console.error('Ошибка при загрузке корзины:', err);
      setError('Не удалось загрузить корзину');
    } finally {
      setLoading(false);
    }
  }, []);

  // Загрузка сводки корзины (легковесный запрос)
  const fetchCartSummary = useCallback(async () => {
    try {
      const response = await cartAPI.getCartSummary();
      setCartSummary(response.data);
    } catch (err) {
      console.error('Ошибка при загрузке сводки корзины:', err);
    }
  }, []);

  // Добавление товара в корзину
  const addToCart = useCallback(async (productId, quantity = 1) => {
    try {
      setLoading(true);
      const response = await cartAPI.addToCart(productId, quantity);
      
      if (response.data.success) {
        // Устанавливаем данные корзины из ответа сервера
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });

        // Оповещаем всех, что корзина обновилась
        window.dispatchEvent(new CustomEvent('cart:updated'));
        
        return { success: true, message: response.data.message };
      } else {
        // Получаем детали ошибки из ответа сервера
        const errorMessage = response.data.error || response.data.message || 'Не удалось добавить товар в корзину';
        console.warn('Ошибка при добавлении товара в корзину:', errorMessage);
        
        return { 
          success: false, 
          message: errorMessage,
          error: errorMessage // Добавляем для обратной совместимости
        };
      }
    } catch (err) {
      console.error('Ошибка при добавлении товара в корзину:', err);
      return { 
        success: false, 
        message: 'Ошибка при добавлении товара в корзину',
        error: err.message || 'Неизвестная ошибка'
      };
    } finally {
      setLoading(false);
    }
  }, []);

  // Обновление количества товара в корзине
  const updateCartItem = useCallback(async (itemId, quantity) => {
    try {
      setLoading(true);
      const response = await cartAPI.updateCartItem(itemId, quantity);
      
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });

        // Оповещаем всех, что корзина обновилась
        window.dispatchEvent(new CustomEvent('cart:updated'));
        
        return { success: true, message: response.data.message };
      } else {
        return { success: false, message: response.data.error || 'Не удалось обновить количество товара' };
      }
    } catch (err) {
      console.error('Ошибка при обновлении количества товара:', err);
      return { success: false, message: 'Ошибка при обновлении количества товара' };
    } finally {
      setLoading(false);
    }
  }, []);

  // Удаление товара из корзины
  const removeFromCart = useCallback(async (itemId) => {
    try {
      setLoading(true);
      const response = await cartAPI.removeFromCart(itemId);
      
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });

        // Оповещаем всех, что корзина обновилась
        window.dispatchEvent(new CustomEvent('cart:updated'));
        
        return { success: true, message: response.data.message };
      } else {
        return { success: false, message: response.data.error || 'Не удалось удалить товар из корзины' };
      }
    } catch (err) {
      console.error('Ошибка при удалении товара из корзины:', err);
      return { success: false, message: 'Ошибка при удалении товара из корзины' };
    } finally {
      setLoading(false);
    }
  }, []);

  // Очистка корзины
  const clearCart = useCallback(async () => {
    try {
      setLoading(true);
      const response = await cartAPI.clearCart();
      
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({ total_items: 0, total_price: 0 });
        
        // Оповещаем всех, что корзина обновилась (очищена)
        window.dispatchEvent(new CustomEvent('cart:updated'));
        
        return { success: true, message: response.data.message };
      } else {
        return { success: false, message: response.data.error || 'Не удалось очистить корзину' };
      }
    } catch (err) {
      console.error('Ошибка при очистке корзины:', err);
      return { success: false, message: 'Ошибка при очистке корзины' };
    } finally {
      setLoading(false);
    }
  }, []);

  // Объединение корзин при авторизации
  const mergeCarts = useCallback(async () => {
    if (!user) return;
    
    try {
      // Получаем session_id из cookie
      const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
      };
      
      const sessionId = getCookie('cart_session_id');
      console.log('Объединение корзин с session_id:', sessionId);
      
      const response = await cartAPI.mergeCarts(sessionId);
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
      }
    } catch (err) {
      console.error('Ошибка при объединении корзин:', err);
    }
  }, [user]);

  // Загружаем корзину при монтировании компонента
  useEffect(() => {
    // Функция для получения корзины с обработкой ошибок
    const loadCart = async () => {
      try {
        await fetchCart();
      } catch (err) {
        console.error('Не удалось загрузить корзину при инициализации', err);
        setLoading(false);
      }
    };
    
    loadCart();
  }, [fetchCart]);

  // Объединяем корзины при авторизации пользователя
  useEffect(() => {
    // Объединяем корзины сразу при изменении пользователя
    if (user) {
      console.log('Пользователь изменился, объединяем корзины');
      mergeCarts()
        .then(() => {
          // После объединения корзин перезагружаем корзину
          fetchCart();
          // Оповещаем всех, что корзина обновилась после объединения
          window.dispatchEvent(new CustomEvent('cart:merged'));
        })
        .catch(err => {
          console.error('Не удалось объединить корзины', err);
        });
    }
  }, [user, mergeCarts, fetchCart]);

  // Значение контекста
  const value = {
    cart,
    cartSummary,
    loading,
    error,
    fetchCart,
    fetchCartSummary,
    addToCart,
    updateCartItem,
    removeFromCart,
    clearCart
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export default CartContext; 