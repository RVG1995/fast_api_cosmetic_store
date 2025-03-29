import { useState, useCallback, useEffect } from 'react';
import { cartAPI } from '../utils/api';

export const useCartOperations = () => {
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cartSummary, setCartSummary] = useState({ total_items: 0, total_price: 0 });
  const [lastOperation, setLastOperation] = useState(null);

  // Загрузка данных корзины
  const fetchCart = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await cartAPI.getCart();
      
      if (response && response.data) {
        setCart(response.data);
        
        // Обновляем сводку корзины
        setCartSummary({
          total_items: response.data.total_items || 0,
          total_price: response.data.total_price || 0
        });
      } else {
        setError('Не удалось загрузить данные корзины');
      }
    } catch (err) {
      console.error('Ошибка при загрузке корзины:', err);
      setError('Не удалось загрузить корзину');
    } finally {
      setLoading(false);
    }
  }, []);

  // Добавление товара в корзину
  const addToCart = useCallback(async (productId, quantity = 1) => {
    try {
      setLoading(true);
      setError(null);
      setLastOperation({ type: 'add', productId, quantity });
      
      const response = await cartAPI.addToCart(productId, quantity);
      
      if (response && response.data && response.data.success) {
        setCart(response.data.cart);
        
        const cartSummaryData = {
          total_items: response.data.cart.total_items || 
                      (response.data.cart.items ? response.data.cart.items.length : 0),
          total_price: response.data.cart.total_price || 0
        };
        
        setCartSummary(cartSummaryData);
        
        // Оповещаем всех об обновлении корзины
        window.dispatchEvent(new CustomEvent('cart:updated', { 
          detail: {
            cart: response.data.cart,
            summary: cartSummaryData
          }
        }));
        
        return { success: true, message: response.data.message };
      } else {
        const errorMessage = response?.data?.error || response?.data?.message || 'Не удалось добавить товар в корзину';
        setError(errorMessage);
        return { 
          success: false, 
          message: errorMessage,
          error: errorMessage
        };
      }
    } catch (err) {
      console.error('Ошибка при добавлении товара в корзину:', err);
      setError(err.message || 'Ошибка при добавлении товара в корзину');
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
      setError(null);
      setLastOperation({ type: 'update', itemId, quantity });
      
      const response = await cartAPI.updateCartItem(itemId, quantity);
      
      if (response && response.data && response.data.success) {
        setCart(response.data.cart);
        
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
        
        // Оповещаем всех об обновлении корзины
        window.dispatchEvent(new CustomEvent('cart:updated', { 
          detail: {
            cart: response.data.cart,
            summary: {
              total_items: response.data.cart.total_items || 0,
              total_price: response.data.cart.total_price || 0
            }
          }
        }));
        
        return { success: true, message: response.data.message };
      } else {
        const errorMessage = response?.data?.error || 'Не удалось обновить количество товара';
        setError(errorMessage);
        return { success: false, message: errorMessage };
      }
    } catch (err) {
      console.error('Ошибка при обновлении количества товара:', err);
      setError(err.message || 'Ошибка при обновлении количества товара');
      return { success: false, message: 'Ошибка при обновлении количества товара' };
    } finally {
      setLoading(false);
    }
  }, []);

  // Удаление товара из корзины
  const removeFromCart = useCallback(async (itemId) => {
    try {
      setLoading(true);
      setError(null);
      setLastOperation({ type: 'remove', itemId });
      
      const response = await cartAPI.removeFromCart(itemId);
      
      if (response && response.data && response.data.success) {
        setCart(response.data.cart);
        
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
        
        // Оповещаем всех об обновлении корзины
        window.dispatchEvent(new CustomEvent('cart:updated', { 
          detail: {
            cart: response.data.cart,
            summary: {
              total_items: response.data.cart.total_items || 0,
              total_price: response.data.cart.total_price || 0
            }
          }
        }));
        
        return { success: true, message: response.data.message };
      } else {
        const errorMessage = response?.data?.error || 'Не удалось удалить товар из корзины';
        setError(errorMessage);
        return { success: false, message: errorMessage };
      }
    } catch (err) {
      console.error('Ошибка при удалении товара из корзины:', err);
      setError(err.message || 'Ошибка при удалении товара из корзины');
      return { success: false, message: 'Ошибка при удалении товара из корзины' };
    } finally {
      setLoading(false);
    }
  }, []);

  // Очистка корзины
  const clearCart = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setLastOperation({ type: 'clear' });
      
      const response = await cartAPI.clearCart();
      
      if (response && response.data && response.data.success) {
        setCart(response.data.cart);
        setCartSummary({ total_items: 0, total_price: 0 });
        
        // Оповещаем всех об обновлении корзины
        window.dispatchEvent(new CustomEvent('cart:updated'));
        
        return { success: true, message: response.data.message };
      } else {
        const errorMessage = response?.data?.error || 'Не удалось очистить корзину';
        setError(errorMessage);
        return { success: false, message: errorMessage };
      }
    } catch (err) {
      console.error('Ошибка при очистке корзины:', err);
      setError(err.message || 'Ошибка при очистке корзины');
      return { success: false, message: 'Ошибка при очистке корзины' };
    } finally {
      setLoading(false);
    }
  }, []);

  // Загружаем корзину при первом рендере
  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  return {
    cart,
    cartSummary,
    loading,
    error,
    fetchCart,
    addToCart,
    updateCartItem,
    removeFromCart,
    clearCart,
    lastOperation
  };
};

export default useCartOperations; 