/**
 * Функции для работы со slug
 */

/**
 * Карта транслитерации русских символов в латиницу
 */
const transliterationMap = {
  'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
  'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
  'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
  'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
  'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
  ' ': '-', '_': '-', '/': '-'
};

/**
 * Транслитерация строки из кириллицы в латиницу
 * 
 * @param {string} text - исходная строка на кириллице
 * @returns {string} - транслитерированная строка
 */
export const transliterate = (text) => {
  return text.toLowerCase().split('').map(char => {
    const lowerChar = char.toLowerCase();
    return transliterationMap[lowerChar] !== undefined ? transliterationMap[lowerChar] : char;
  }).join('');
};

/**
 * Создание slug из строки текста
 * Поддерживает как русский, так и английский текст
 * 
 * @param {string} text - исходная строка
 * @returns {string} - slug для использования в URL
 */
export const generateSlug = (text) => {
  if (!text) return '';
  
  // Сначала транслитерируем текст, если он содержит кириллицу
  const containsCyrillic = /[а-яА-ЯёЁ]/.test(text);
  const processedText = containsCyrillic ? transliterate(text) : text;
  
  // Затем преобразуем в валидный slug
  return processedText
    .toLowerCase()
    .replace(/[^\w\s-]/g, '') // Удаляем спецсимволы
    .replace(/[\s_-]+/g, '-')  // Заменяем пробелы и подчеркивания на дефисы
    .replace(/^-+|-+$/g, '');  // Удаляем дефисы в начале и конце строки
}; 