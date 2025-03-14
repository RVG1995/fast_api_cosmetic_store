/**
 * Форматирует дату и время в читабельный вид
 * 
 * @param {string|Date} dateTime - Дата и время для форматирования
 * @param {boolean} includeTime - Включать ли время в результат (по умолчанию true)
 * @returns {string} Отформатированная дата и время
 */
export const formatDateTime = (dateTime, includeTime = true) => {
  if (!dateTime) return '';

  try {
    const date = new Date(dateTime);
    
    // Проверка валидности даты
    if (isNaN(date.getTime())) {
      return 'Некорректная дата';
    }
    
    // Опции для форматирования даты
    const dateOptions = { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric'
    };
    
    // Если нужно включить время, добавляем опции времени
    if (includeTime) {
      return `${date.toLocaleDateString('ru-RU', dateOptions)} ${date.toLocaleTimeString('ru-RU', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })}`;
    }
    
    // Если время не нужно, возвращаем только дату
    return date.toLocaleDateString('ru-RU', dateOptions);
  } catch (error) {
    console.error('Ошибка при форматировании даты:', error);
    return 'Ошибка форматирования';
  }
};

/**
 * Форматирует дату в читабельный вид без времени
 * 
 * @param {string|Date} date - Дата для форматирования
 * @returns {string} Отформатированная дата
 */
export const formatDate = (date) => {
  return formatDateTime(date, false);
};

/**
 * Возвращает относительное время (например, "5 минут назад")
 * 
 * @param {string|Date} dateTime - Дата и время
 * @returns {string} Относительное время
 */
export const getRelativeTime = (dateTime) => {
  if (!dateTime) return '';

  try {
    const date = new Date(dateTime);
    
    // Проверка валидности даты
    if (isNaN(date.getTime())) {
      return 'Некорректная дата';
    }
    
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    
    // Меньше минуты
    if (diffSec < 60) {
      return 'Только что';
    }
    
    // Меньше часа
    if (diffSec < 3600) {
      const minutes = Math.floor(diffSec / 60);
      return `${minutes} ${getEnding(minutes, ['минуту', 'минуты', 'минут'])} назад`;
    }
    
    // Меньше суток
    if (diffSec < 86400) {
      const hours = Math.floor(diffSec / 3600);
      return `${hours} ${getEnding(hours, ['час', 'часа', 'часов'])} назад`;
    }
    
    // Меньше недели
    if (diffSec < 604800) {
      const days = Math.floor(diffSec / 86400);
      return `${days} ${getEnding(days, ['день', 'дня', 'дней'])} назад`;
    }
    
    // Возвращаем полную дату для более старых дат
    return formatDateTime(date);
  } catch (error) {
    console.error('Ошибка при расчете относительного времени:', error);
    return 'Ошибка форматирования';
  }
};

/**
 * Вспомогательная функция для правильного склонения слов
 * 
 * @param {number} number - Число для которого выбираем склонение
 * @param {Array<string>} titles - Массив вариантов склонения [1, 2-4, 5-0]
 * @returns {string} Правильно склоненное слово
 */
const getEnding = (number, titles) => {
  const cases = [2, 0, 1, 1, 1, 2];
  return titles[
    number % 100 > 4 && number % 100 < 20 
      ? 2 
      : cases[Math.min(number % 10, 5)]
  ];
}; 