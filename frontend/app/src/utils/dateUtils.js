/**
 * Форматирует дату в формате DD.MM.YYYY
 * @param {string} dateString - Строка с датой в формате ISO
 * @returns {string} Отформатированная дата
 */
export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  // Проверка на валидность даты
  if (isNaN(date.getTime())) {
    return '';
  }
  
  // Добавляем ведущий ноль при необходимости
  const padZero = (num) => {
    return num < 10 ? `0${num}` : num;
  };
  
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
  
  // Добавляем ведущий ноль при необходимости
  const padZero = (num) => {
    return num < 10 ? `0${num}` : num;
  };
  
  const day = padZero(date.getDate());
  const month = padZero(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = padZero(date.getHours());
  const minutes = padZero(date.getMinutes());
  
  return `${day}.${month}.${year} ${hours}:${minutes}`;
};

/**
 * Возвращает относительную дату (например, "2 дня назад")
 * @param {string} dateString - Строка с датой в формате ISO
 * @returns {string} Относительная дата
 */
export const getRelativeDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  // Проверка на валидность даты
  if (isNaN(date.getTime())) {
    return '';
  }
  
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  // Менее минуты назад
  if (diffInSeconds < 60) {
    return 'только что';
  }
  
  // Менее часа
  if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes} ${getDeclension(minutes, ['минуту', 'минуты', 'минут'])} назад`;
  }
  
  // Менее суток
  if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours} ${getDeclension(hours, ['час', 'часа', 'часов'])} назад`;
  }
  
  // Менее 30 дней
  if (diffInSeconds < 2592000) {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days} ${getDeclension(days, ['день', 'дня', 'дней'])} назад`;
  }
  
  // Менее года
  if (diffInSeconds < 31536000) {
    const months = Math.floor(diffInSeconds / 2592000);
    return `${months} ${getDeclension(months, ['месяц', 'месяца', 'месяцев'])} назад`;
  }
  
  // Более года
  const years = Math.floor(diffInSeconds / 31536000);
  return `${years} ${getDeclension(years, ['год', 'года', 'лет'])} назад`;
};

/**
 * Возвращает правильное склонение слова в зависимости от числа
 * @param {number} number - Число
 * @param {Array} words - Массив слов в формате [один, два-четыре, пять-двадцать]
 * @returns {string} Склоненное слово
 */
const getDeclension = (number, words) => {
  const cases = [2, 0, 1, 1, 1, 2];
  return words[(number % 100 > 4 && number % 100 < 20) ? 2 : cases[Math.min(number % 10, 5)]];
}; 