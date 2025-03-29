import { useState, useEffect, useRef } from 'react';

/**
 * Хук для отслеживания видимости элемента с помощью Intersection Observer API
 * Может использоваться для ленивой загрузки или бесконечного скролла
 * 
 * @param {Object} options - Опции для Intersection Observer
 * @param {number} options.threshold - Порог пересечения (0-1)
 * @param {string} options.root - Элемент, относительно которого проверяется видимость
 * @param {string} options.rootMargin - Отступы вокруг root элемента ('10px 20px 30px 40px')
 * @param {boolean} options.triggerOnce - Сработать только один раз
 * @returns {[React.RefObject, boolean, IntersectionObserverEntry]} Реф для отслеживаемого элемента, флаг видимости, данные о пересечении
 */
function useIntersectionObserver({
  threshold = 0,
  root = null,
  rootMargin = '0px',
  triggerOnce = false,
} = {}) {
  const [isVisible, setIsVisible] = useState(false);
  const [entry, setEntry] = useState(null);
  const elementRef = useRef(null);
  const frozen = useRef(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || frozen.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setEntry(entry);
        setIsVisible(entry.isIntersecting);

        // Если элемент виден и настроен на однократное срабатывание,
        // замораживаем отслеживание
        if (entry.isIntersecting && triggerOnce) {
          frozen.current = true;
          observer.unobserve(element);
        }
      },
      { threshold, root, rootMargin }
    );

    observer.observe(element);

    return () => {
      if (element) {
        observer.unobserve(element);
      }
    };
  }, [threshold, root, rootMargin, triggerOnce]);

  return [elementRef, isVisible, entry];
}

export default useIntersectionObserver; 