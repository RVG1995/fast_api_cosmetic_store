import { useEffect } from 'react';
import { useCart } from '../../context/CartContext';

/**
 * Компонент, который обновляет данные корзины при монтировании
 * Может быть добавлен в любой компонент, где нужно гарантировать актуальность корзины
 */
const CartUpdater = () => {
  const { fetchCart } = useCart();

  useEffect(() => {
    // При монтировании компонента обновляем корзину
    fetchCart();
  }, [fetchCart]);

  // Компонент не отображает никакого UI
  return null;
};

export default CartUpdater; 