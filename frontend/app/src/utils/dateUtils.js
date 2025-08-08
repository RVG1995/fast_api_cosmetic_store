/**
 * Форматирует дату в формате DD.MM.YYYY
 * @param {string} dateString - Строка с датой в формате ISO
 * @returns {string} Отформатированная дата
 */
// Общий helper
const padZero = (num) => (num < 10 ? `0${num}` : num);

export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  // Проверка на валидность даты
  if (isNaN(date.getTime())) {
    return '';
  }
  
  const day = padZero(date.getDate());
  const month = padZero(date.getMonth() + 1);
  const year = date.getFullYear();
  
  return `${day}.${month}.${year}`;
};

/**
 * Форматирует дату и время в формате DD.MM.YYYY HH:MM
 * @param {string} dateString - Строка с датой в формате ISO
 * @returns {string} Отформатированная дата и время
 */
export const formatDateTime = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  // Проверка на валидность даты
  if (isNaN(date.getTime())) {
    return '';
  }
  
  const day = padZero(date.getDate());
  const month = padZero(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = padZero(date.getHours());
  const minutes = padZero(date.getMinutes());
  
  return `${day}.${month}.${year} ${hours}:${minutes}`;
};

 