import React, { createContext, useContext, useState, useEffect } from 'react';
import { productAPI } from '../utils/api';

// Создаем контекст для категорий
const CategoryContext = createContext();

// Хук для использования контекста категорий
export const useCategories = () => {
  return useContext(CategoryContext);
};

// Провайдер контекста категорий
export const CategoryProvider = ({ children }) => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Функция для загрузки категорий
  const fetchCategories = async () => {
    try {
      setLoading(true);
      const response = await productAPI.getCategories();
      setCategories(response.data);
      setError(null);
    } catch (err) {
      console.error('Ошибка при загрузке категорий:', err);
      setError('Не удалось загрузить категории');
    } finally {
      setLoading(false);
    }
  };

  // Загружаем категории при монтировании компонента
  useEffect(() => {
    fetchCategories();
  }, []);

  // Функция для добавления категории
  const addCategory = (newCategory) => {
    setCategories([...categories, newCategory]);
  };

  // Функция для обновления категории
  const updateCategory = (updatedCategory) => {
    setCategories(categories.map(cat => 
      cat.id === updatedCategory.id ? updatedCategory : cat
    ));
  };

  // Функция для удаления категории
  const deleteCategory = (categoryId) => {
    setCategories(categories.filter(cat => cat.id !== categoryId));
  };

  // Значение, которое будет доступно через контекст
  const value = {
    categories,
    loading,
    error,
    fetchCategories,
    addCategory,
    updateCategory,
    deleteCategory
  };

  return (
    <CategoryContext.Provider value={value}>
      {children}
    </CategoryContext.Provider>
  );
}; 