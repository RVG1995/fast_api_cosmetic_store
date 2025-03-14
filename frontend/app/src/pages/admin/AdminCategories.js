import React, { useState } from 'react';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProducts.css'; // Используем те же стили, что и для товаров
import axios from 'axios';
import { Alert, Button, Modal, Form, Table } from 'react-bootstrap';
import { generateSlug } from '../../utils/slugUtils';
import { useCategories } from '../../context/CategoryContext';

const AdminCategories = () => {
  const { categories, loading, error, fetchCategories, addCategory, updateCategory, deleteCategory } = useCategories();
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('add'); // 'add' или 'edit'
  const [formData, setFormData] = useState({
    name: '',
    slug: ''
  });

  // Обработчик изменения полей формы
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    setFormData({
      ...formData,
      [name]: value
    });
    
    // Если изменилось имя, автоматически генерируем slug
    if (name === 'name') {
      const slug = generateSlug(value);
      
      setFormData(prev => ({
        ...prev,
        slug
      }));
    }
  };

  // Открытие модального окна для добавления новой категории
  const handleAddCategory = () => {
    setModalMode('add');
    setFormData({
      name: '',
      slug: ''
    });
    setIsModalOpen(true);
  };

  // Открытие модального окна для редактирования категории
  const handleEditCategory = (category) => {
    setModalMode('edit');
    setSelectedCategory(category);
    setFormData({
      name: category.name,
      slug: category.slug
    });
    setIsModalOpen(true);
  };

  // Сохранение категории (добавление или обновление)
  const handleSaveCategory = async () => {
    try {
      // Проверяем, что все необходимые поля заполнены
      if (!formData.name || !formData.slug) {
        alert('Пожалуйста, заполните все поля формы.');
        return;
      }
      
      if (modalMode === 'add') {
        const response = await productAPI.createCategory(formData);
        addCategory(response.data);
      } else {
        const response = await productAPI.updateCategory(selectedCategory.id, formData);
        updateCategory(response.data);
      }
      setIsModalOpen(false);
    } catch (err) {
      console.error('Ошибка при сохранении категории:', err);
      alert(`Не удалось сохранить категорию: ${err.message || 'Проверьте введенные данные и права доступа.'}`);
    }
  };

  // Удаление категории
  const handleDeleteCategory = async (categoryId) => {
    if (window.confirm('Вы уверены, что хотите удалить эту категорию? Это также удалит все связанные подкатегории и товары.')) {
      try {
        await productAPI.deleteCategory(categoryId);
        deleteCategory(categoryId);
      } catch (err) {
        console.error('Ошибка при удалении категории:', err);
        alert('Не удалось удалить категорию. Возможно, она используется в товарах или подкатегориях.');
      }
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="admin-products-page container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Управление категориями</h2>
        <button 
          className="btn btn-primary" 
          onClick={handleAddCategory}
        >
          <i className="bi bi-plus-circle me-2"></i>
          Добавить категорию
        </button>
      </div>

      {categories.length === 0 ? (
        <div className="alert alert-info">
          Категории отсутствуют. Добавьте новую категорию, нажав на кнопку выше.
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-striped table-hover">
            <thead className="table-primary">
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Slug</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {categories.map(category => (
                <tr key={category.id}>
                  <td>{category.id}</td>
                  <td>{category.name}</td>
                  <td>{category.slug}</td>
                  <td>
                    <button 
                      className="btn btn-sm btn-outline-primary me-2" 
                      onClick={() => handleEditCategory(category)}
                    >
                      <i className="bi bi-pencil"></i>
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-danger" 
                      onClick={() => handleDeleteCategory(category.id)}
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Модальное окно для добавления/редактирования категории */}
      {isModalOpen && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {modalMode === 'add' ? 'Добавить новую категорию' : 'Редактировать категорию'}
                </h5>
                <button 
                  type="button" 
                  className="btn-close" 
                  onClick={() => setIsModalOpen(false)}
                ></button>
              </div>
              <div className="modal-body">
                <form>
                  <div className="mb-3">
                    <label htmlFor="name" className="form-label">Название</label>
                    <input
                      type="text"
                      className="form-control"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  
                  <div className="mb-3">
                    <label htmlFor="slug" className="form-label">Slug (для URL)</label>
                    <input
                      type="text"
                      className="form-control"
                      id="slug"
                      name="slug"
                      value={formData.slug}
                      onChange={handleInputChange}
                      required
                    />
                    <div className="form-text">
                      Slug автоматически генерируется из названия, но вы можете изменить его вручную.
                    </div>
                  </div>
                </form>
              </div>
              <div className="modal-footer">
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setIsModalOpen(false)}
                >
                  Отмена
                </button>
                <button 
                  type="button" 
                  className="btn btn-primary" 
                  onClick={handleSaveCategory}
                >
                  {modalMode === 'add' ? 'Добавить' : 'Сохранить'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminCategories; 