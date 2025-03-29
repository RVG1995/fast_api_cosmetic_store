import React, { useRef, useEffect, useState, memo } from 'react';
import PropTypes from 'prop-types';
import './Transition.css';

/**
 * Компонент для анимированного перехода между состояниями или компонентами
 */
const Transition = ({
  show = true,
  children,
  type = 'fade', // fade, slide, zoom, etc.
  duration = 300,
  className = '',
  unmountOnExit = true,
  onEnter = () => {},
  onEntered = () => {},
  onExit = () => {},
  onExited = () => {},
}) => {
  const [status, setStatus] = useState(show ? 'entering' : 'exited');
  const timeoutRef = useRef(null);
  const nodeRef = useRef(null);
  
  const clearTimeouts = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };
  
  // Запускаем анимацию при изменении show
  useEffect(() => {
    clearTimeouts();
    
    if (show) {
      // Компонент должен появиться
      setStatus('entering');
      onEnter();
      
      // После задержки устанавливаем состояние 'entered'
      timeoutRef.current = setTimeout(() => {
        setStatus('entered');
        onEntered();
      }, duration);
    } else {
      // Компонент должен исчезнуть
      if (status !== 'exited') {
        setStatus('exiting');
        onExit();
        
        // После задержки устанавливаем состояние 'exited'
        timeoutRef.current = setTimeout(() => {
          setStatus('exited');
          onExited();
        }, duration);
      }
    }
    
    return clearTimeouts;
  }, [show, duration, onEnter, onEntered, onExit, onExited, status]);
  
  // Если компонент полностью скрыт и unmountOnExit=true, не рендерим его
  if (status === 'exited' && unmountOnExit) {
    return null;
  }
  
  // Определяем классы для анимации
  const transitionClasses = [
    'transition',
    `transition-${type}`,
    `transition-${status}`,
    className
  ].filter(Boolean).join(' ');
  
  // Устанавливаем стили для длительности анимации
  const style = {
    '--transition-duration': `${duration}ms`,
  };
  
  return (
    <div 
      className={transitionClasses} 
      style={style}
      ref={nodeRef}
    >
      {children}
    </div>
  );
};

Transition.propTypes = {
  show: PropTypes.bool,
  children: PropTypes.node,
  type: PropTypes.oneOf(['fade', 'slide', 'zoom', 'slide-down', 'slide-up', 'slide-left', 'slide-right']),
  duration: PropTypes.number,
  className: PropTypes.string,
  unmountOnExit: PropTypes.bool,
  onEnter: PropTypes.func,
  onEntered: PropTypes.func,
  onExit: PropTypes.func,
  onExited: PropTypes.func,
};

export default memo(Transition); 