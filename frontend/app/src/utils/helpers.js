/**
 * Форматирует цену, добавляя разделители тысяч
 * @param {number} price - Цена для форматирования
 * @returns {string} - Отформатированная цена
 */
export const formatPrice = (price) => {
  if (price === undefined || price === null) return '0';
  return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
};

 