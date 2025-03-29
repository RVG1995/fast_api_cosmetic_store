import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Компонент для автоматической прокрутки страницы вверх при навигации
 * Должен быть добавлен в корневой компонент (App.js) внутри BrowserRouter
 */
function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    // Прокручиваем страницу вверх при изменении маршрута
    window.scrollTo(0, 0);
    
    // При медленном интернете бывает, что контент еще не загрузился полностью
    // Попробуем прокрутить еще раз через небольшую задержку
    const timeoutId = setTimeout(() => {
      window.scrollTo(0, 0);
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [pathname]);

  return null; // Этот компонент не отображает никакого UI
}

export default ScrollToTop; 