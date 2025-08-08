import React, { useRef, useEffect, useState, cloneElement, memo } from 'react';
import PropTypes from 'prop-types';
import './TransitionGroup.css';

/**
 * Компонент для анимации списков элементов
 * Обеспечивает анимированное добавление/удаление элементов в списке
 */
const TransitionGroup = ({
  children,
  component = 'div',
  className = '',
  childFactory = child => child,
  appear = false,
  exit = true,
  ...props
}) => {
  // Map для отслеживания ключей и состояний элементов
  const [childrenMap, setChildrenMap] = useState(new Map());
  
  // Ref для предыдущих дочерних элементов
  const prevChildrenRef = useRef([]);
  
  // Обновляем карту элементов при изменении дочерних элементов
  useEffect(() => {
    const childrenArray = React.Children.toArray(children);
    const prevChildrenArray = prevChildrenRef.current;
    
    // Новые элементы, которых не было ранее
    const newChildren = childrenArray.filter(
      child => !prevChildrenArray.some(prevChild => 
        prevChild.key === child.key
      )
    );
    
    // Элементы, которые были удалены
    const removedChildren = prevChildrenArray.filter(
      prevChild => !childrenArray.some(child => 
        child.key === prevChild.key
      )
    );
    
    // Обновляем карту с состояниями элементов
    const newMap = new Map(childrenMap);
    
    // Добавляем новые элементы
    newChildren.forEach(child => {
      if (child.key) {
        newMap.set(child.key, { child, status: appear ? 'entering' : 'entered' });
        
        // Если нужна анимация появления, устанавливаем таймер для перехода в 'entered'
        if (appear) {
          setTimeout(() => {
            setChildrenMap(prev => {
              const updated = new Map(prev);
              const item = updated.get(child.key);
              if (item) {
                updated.set(child.key, { ...item, status: 'entered' });
              }
              return updated;
            });
          }, 50); // Небольшая задержка для применения анимации
        }
      }
    });
    
    // Обрабатываем удаленные элементы
    removedChildren.forEach(child => {
      if (child.key && exit) {
        // Устанавливаем состояние 'exiting' для удаленных элементов
        const item = newMap.get(child.key);
        if (item) {
          newMap.set(child.key, { ...item, status: 'exiting' });
          
          // Удаляем элемент из карты после завершения анимации
          setTimeout(() => {
            setChildrenMap(prev => {
              const updated = new Map(prev);
              updated.delete(child.key);
              return updated;
            });
          }, 300); // Длительность анимации (можно вынести в переменную)
        }
      } else if (child.key) {
        // Если анимация выхода отключена, сразу удаляем элемент
        newMap.delete(child.key);
      }
    });
    
    // Обновляем оставшиеся элементы
    childrenArray.forEach(child => {
      if (child.key && !newChildren.includes(child)) {
        const item = newMap.get(child.key);
        if (item) {
          newMap.set(child.key, { ...item, child });
        }
      }
    });
    
    // Обновляем состояние и ссылку на предыдущие элементы
    setChildrenMap(newMap);
    prevChildrenRef.current = childrenArray;
  }, [children, appear, exit, childrenMap]);
  
  // Формируем массив дочерних элементов с анимацией
  const childrenToRender = [];
  childrenMap.forEach(({ child, status }, key) => {
    // Добавляем свойства для анимации к дочернему элементу
    const animatedChild = cloneElement(childFactory(child), {
      'data-transition-status': status,
      'data-transition-key': key,
      className: `${child.props.className || ''} transition-item transition-${status}`
    });
    
    childrenToRender.push(animatedChild);
  });
  
  // Рендерим указанный компонент-обертку с анимированными дочерними элементами
  const Component = component;
  return (
    <Component 
      className={`transition-group ${className}`}
      {...props}
    >
      {childrenToRender}
    </Component>
  );
};

TransitionGroup.propTypes = {
  children: PropTypes.node,
  component: PropTypes.oneOfType([PropTypes.string, PropTypes.elementType]),
  className: PropTypes.string,
  childFactory: PropTypes.func,
  appear: PropTypes.bool,
  exit: PropTypes.bool,
};

export default memo(TransitionGroup); 