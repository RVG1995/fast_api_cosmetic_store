import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { cartAPI, productAPI } from '../utils/api';
import { useAuth } from './AuthContext';
import { STORAGE_KEYS } from '../utils/constants';

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

// --- Вспомогательные функции для localStorage ---
const getLocalCart = () => {
  try {
    const data = localStorage.getItem(STORAGE_KEYS.CART_DATA);
    return data ? JSON.parse(data) : { items: [] };
  } catch {
    return { items: [] };
  }
};

const setLocalCart = (cart) => {
  try {
    localStorage.setItem(STORAGE_KEYS.CART_DATA, JSON.stringify(cart));
  } catch {}
};

const clearLocalCart = () => {
  try {
    localStorage.removeItem(STORAGE_KEYS.CART_DATA);
  } catch {}
};

// --- Локальные операции с корзиной ---
const localCartToSummary = (cartObj) => ({
  total_items: cartObj.items.reduce((sum, i) => sum + i.quantity, 0),
  total_price: cartObj.items.reduce((sum, i) => sum + (i.product?.price || 0) * i.quantity, 0)
});

// Провайдер контекста корзины
export const CartProvider = ({ children }) => {
  const { user } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cartSummary, setCartSummary] = useState({ total_items: 0, total_price: 0 });
  const isMergingRef = useRef(false);
  const prevUserId = useRef();

  // --- Получение корзины ---
  const fetchCart = useCallback(async () => {
    console.log('fetchCart вызван, user:', user);
    setLoading(true);
    setError(null);
    if (!user) {
      // Аноним: localStorage
      const localCart = getLocalCart();
      // --- ДОБАВЛЕНО: подгружаем инфу о товарах ---
      if (localCart.items.length > 0) {
        try {
          const ids = localCart.items.map(i => i.product_id);
          const products = await productAPI.getProductsBatch(ids);
          const productsInfo = {};
          products.forEach(p => { if (p) productsInfo[p.id] = p; });
          localCart.items = localCart.items.map(i => ({ ...i, product: productsInfo[i.product_id] || null }));
        } catch (e) {
          localCart.items = localCart.items.map(i => ({ ...i, product: null }));
        }
      }
      // --- ГАРАНТИРУЕМ наличие total_items/total_price в cart ---
      const summary = localCartToSummary(localCart);
      const cartWithTotals = { ...localCart, ...summary };
      setCart(cartWithTotals);
      setCartSummary(summary);
      setLoading(false);
      return;
    }
    // Авторизованный: API
    try {
      const response = await cartAPI.getCart();
      setCart(response.data);
      setCartSummary({
        total_items: response.data.total_items || 0,
        total_price: response.data.total_price || 0
      });
    } catch (err) {
      setError('Не удалось загрузить корзину');
    } finally {
      setLoading(false);
    }
  }, [user]);

  // --- Получение сводки корзины ---
  const fetchCartSummary = useCallback(async () => {
    if (!user) {
      const localCart = getLocalCart();
      setCartSummary(localCartToSummary(localCart));
      return;
    }
    try {
      const response = await cartAPI.getCartSummary();
      if (response.data) setCartSummary(response.data);
    } catch {}
  }, [user]);

  // --- Добавление товара ---
  const addToCart = useCallback(async (productId, quantity = 1) => {
    setLoading(true);
    if (!user) {
      let localCart = getLocalCart();
      const idx = localCart.items.findIndex(i => i.product_id === productId);
      if (idx !== -1) {
        localCart.items[idx].quantity += quantity;
      } else {
        localCart.items.push({ product_id: productId, quantity });
      }
      setLocalCart(localCart);

      // --- ПОДГРУЗКА ИНФЫ О ТОВАРАХ ---
      let productName = "Товар";
      if (localCart.items.length > 0) {
        try {
          const ids = localCart.items.map(i => i.product_id);
          const products = await productAPI.getProductsBatch(ids);
          const productsInfo = {};
          products.forEach(p => { if (p) productsInfo[p.id] = p; });
          localCart.items = localCart.items.map(i => ({ ...i, product: productsInfo[i.product_id] || null }));
          
          // Получаем название добавленного товара
          const addedProduct = productsInfo[productId];
          if (addedProduct && addedProduct.name) {
            productName = addedProduct.name;
          }
        } catch (e) {
          localCart.items = localCart.items.map(i => ({ ...i, product: null }));
        }
      }

      setCart(localCart);
      setCartSummary(localCartToSummary(localCart));
      setLoading(false);
      window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: localCart, summary: localCartToSummary(localCart) } }));
      return { success: true, message: `${productName} добавлен в корзину`, productName };
    }
    try {
      const response = await cartAPI.addToCart(productId, quantity);
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
        window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: response.data.cart, summary: { total_items: response.data.cart.total_items || 0, total_price: response.data.cart.total_price || 0 } } }));
        
        // Определяем название товара из ответа сервера
        let productName = "Товар";
        const item = response.data.cart.items.find(item => item.product_id === productId);
        if (item && item.product && item.product.name) {
          productName = item.product.name;
        }
        
        return { success: true, message: `${productName} добавлен в корзину`, productName };
      } else {
        return { success: false, message: response.data.error || response.data.message || 'Не удалось добавить товар в корзину' };
      }
    } catch (err) {
      return { success: false, message: 'Ошибка при добавлении товара в корзину', error: err.message || 'Неизвестная ошибка' };
    } finally {
      setLoading(false);
    }
  }, [user]);

  // --- Обновление количества ---
  const updateCartItem = useCallback(async (itemId, quantity) => {
    setLoading(true);
    if (!user) {
      let localCart = getLocalCart();
      if (itemId < 0 || itemId >= localCart.items.length) {
        setLoading(false);
        return { success: false, message: 'Товар не найден в корзине' };
      }
      localCart.items[itemId].quantity = quantity;
      setLocalCart(localCart);
      setCart(localCart);
      setCartSummary(localCartToSummary(localCart));
      setLoading(false);
      window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: localCart, summary: localCartToSummary(localCart) } }));
      return { success: true, message: 'Количество товара обновлено' };
    }
    try {
      const response = await cartAPI.updateCartItem(itemId, quantity);
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
        window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: response.data.cart, summary: { total_items: response.data.cart.total_items || 0, total_price: response.data.cart.total_price || 0 } } }));
        return { success: true, message: response.data.message };
      } else {
        return { success: false, message: response.data.error || 'Не удалось обновить количество товара' };
      }
    } catch (err) {
      return { success: false, message: 'Ошибка при обновлении количества товара' };
    } finally {
      setLoading(false);
    }
  }, [user]);

  // --- Удаление товара ---
  const removeFromCart = useCallback(async (itemId) => {
    setLoading(true);
    if (!user) {
      let localCart = getLocalCart();
      if (itemId < 0 || itemId >= localCart.items.length) {
        setLoading(false);
        return { success: false, message: 'Товар не найден в корзине' };
      }
      localCart.items.splice(itemId, 1);
      setLocalCart(localCart);
      setCart(localCart);
      setCartSummary(localCartToSummary(localCart));
      setLoading(false);
      window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: localCart, summary: localCartToSummary(localCart) } }));
      return { success: true, message: 'Товар удален из корзины' };
    }
    try {
      const response = await cartAPI.removeFromCart(itemId);
      if (response.data.success) {
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
        window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: response.data.cart, summary: { total_items: response.data.cart.total_items || 0, total_price: response.data.cart.total_price || 0 } } }));
        return { success: true, message: response.data.message };
      } else {
        return { success: false, message: response.data.error || 'Не удалось удалить товар из корзины' };
      }
    } catch (err) {
      return { success: false, message: 'Ошибка при удалении товара из корзины' };
    } finally {
      setLoading(false);
    }
  }, [user]);

  // --- Очистка корзины ---
  const clearCart = useCallback(async () => {
    setLoading(true);
    if (!user) {
      clearLocalCart();
      setCart({ items: [] });
      setCartSummary({ total_items: 0, total_price: 0 });
      setLoading(false);
      window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: { items: [] }, summary: { total_items: 0, total_price: 0 } } }));
      return { success: true, message: 'Корзина очищена' };
    }
    try {
      const response = await cartAPI.clearCart();
      if (response.data.success) {
        // Принудительно устанавливаем пустую корзину независимо от ответа сервера
        const emptyCart = { items: [] };
        setCart(emptyCart);
        setCartSummary({ total_items: 0, total_price: 0 });
        window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: emptyCart, summary: { total_items: 0, total_price: 0 } } }));
        return { success: true, message: response.data.message };
      } else {
        return { success: false, message: response.data.error || 'Не удалось очистить корзину' };
      }
    } catch (err) {
      console.error('Ошибка при очистке корзины:', err);
      // Даже при ошибке API очищаем корзину на фронтенде, чтобы избежать рассинхронизации
      const emptyCart = { items: [] };
      setCart(emptyCart);
      setCartSummary({ total_items: 0, total_price: 0 });
      window.dispatchEvent(new CustomEvent('cart:updated', { detail: { cart: emptyCart, summary: { total_items: 0, total_price: 0 } } }));
      return { success: false, message: 'Ошибка при очистке корзины' };
    } finally {
      setLoading(false);
    }
  }, [user]);

  // --- Объединение корзин при авторизации ---
  const mergeCarts = useCallback(async () => {
    if (!user) return;
    if (localStorage.getItem('cart_merged')) return;
    if (isMergingRef.current) return;
    isMergingRef.current = true;
    localStorage.setItem('cart_merged', '1');
    const localCart = getLocalCart();
    const validItems = (localCart.items || []).filter(i => Number.isInteger(i.product_id) && Number.isInteger(i.quantity) && i.quantity > 0);
    if (!validItems.length) {
      isMergingRef.current = false;
      return;
    }
    try {
      const response = await cartAPI.mergeCarts(validItems);
      if (response.data.success) {
        clearLocalCart();
        setCart(response.data.cart);
        setCartSummary({
          total_items: response.data.cart.total_items || 0,
          total_price: response.data.cart.total_price || 0
        });
        window.dispatchEvent(new CustomEvent('cart:merged'));
      }
    } catch (err) {
      localStorage.removeItem('cart_merged');
      console.error('Ошибка при объединении корзин:', err);
    } finally {
      isMergingRef.current = false;
    }
  }, [user]);

  // Для избежания сложного выражения в зависимостях useEffect
  const userId = user ? user.id : null;

  // Загружаем корзину при монтировании компонента
  useEffect(() => {
    // Production-safe: вызываем fetchCart только если user.id реально изменился
    if ((user && prevUserId.current === userId) || (!user && prevUserId.current === null)) return;
    prevUserId.current = userId;
    console.log('useEffect(fetchCart) сработал, user:', user);
    fetchCart();
  }, [userId, fetchCart, user]);

  // Объединяем корзины при авторизации пользователя
  useEffect(() => {
    if (user) {
      const localCart = getLocalCart();
      const validItems = (localCart.items || []).filter(i => Number.isInteger(i.product_id) && Number.isInteger(i.quantity) && i.quantity > 0);
      if (validItems.length === 0) {
        // Если localStorage пустой, не вызываем mergeCarts, просто чистим cart_merged
        localStorage.setItem('cart_merged', '1');
        return;
      }
      if (localStorage.getItem('cart_merged')) return;
      mergeCarts();
    } else {
      localStorage.removeItem('cart_merged');
    }
  }, [user, mergeCarts]);

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