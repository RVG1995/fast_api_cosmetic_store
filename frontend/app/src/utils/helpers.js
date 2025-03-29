/**
 * Форматирует цену, добавляя разделители тысяч
 * @param {number} price - Цена для форматирования
 * @returns {string} - Отформатированная цена
 */
export const formatPrice = (price) => {
  if (price === undefined || price === null) return '0';
  return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
};

/**
 * Форматирует дату в локальный формат
 * @param {string} dateString - Строка с датой
 * @returns {string} - Отформатированная дата
 */
export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  // Проверяем корректность даты
  if (isNaN(date.getTime())) {
    return 'Некорректная дата';
  }
  
  // Форматируем дату в формат "DD.MM.YYYY HH:MM"
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${day}.${month}.${year} ${hours}:${minutes}`;
};

/**
 * Обрезает текст до указанной длины и добавляет многоточие
 * @param {string} text - Исходный текст
 * @param {number} maxLength - Максимальная длина
 * @returns {string} - Обрезанный текст
 */
export const truncateText = (text, maxLength) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};

/**
 * Генерирует случайный идентификатор
 * @returns {string} - Случайный идентификатор
 */
export const generateId = () => {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}; 