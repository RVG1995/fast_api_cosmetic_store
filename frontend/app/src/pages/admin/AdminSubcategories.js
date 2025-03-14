import React, { useState, useEffect } from 'react';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProducts.css'; // Используем те же стили, что и для товаров
// Импорты react-bootstrap и axios удалены, так как не используются в компоненте
import { generateSlug } from '../../utils/slugUtils';

const AdminSubcategories = () => {
  const [subcategories, setSubcategories] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('add'); // 'add' или 'edit'
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    category_id: ''
  });

  // Загрузка данных при монтировании компонента
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Загружаем подкатегории и категории параллельно
        const [subcategoriesRes, categoriesRes] = await Promise.all([
          productAPI.getSubcategories(),
          productAPI.getCategories()
        ]);
        
        setSubcategories(subcategoriesRes.data);
        setCategories(categoriesRes.data);
        setError(null);
      } catch (err) {
        console.error('Ошибка при загрузке данных:', err);
        setError('Не удалось загрузить данные. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Получение названия категории по ID
  const getCategoryName = (categoryId) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category ? category.name : 'Не указана';
  };

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

  // Открытие модального окна для добавления новой подкатегории
  const handleAddSubcategory = () => {
    setModalMode('add');
    setFormData({
      name: '',
      slug: '',
      category_id: ''
    });
    setIsModalOpen(true);
  };

  // Открытие модального окна для редактирования подкатегории
  const handleEditSubcategory = (subcategory) => {
    setModalMode('edit');
    setSelectedSubcategory(subcategory);
    setFormData({
      name: subcategory.name,
      slug: subcategory.slug,
      category_id: subcategory.category_id
    });
    setIsModalOpen(true);
  };

  // Сохранение подкатегории (добавление или обновление)
  const handleSaveSubcategory = async () => {
    try {
      // Проверяем, что все необходимые поля заполнены
      if (!formData.name || !formData.slug || !formData.category_id) {
        alert('Пожалуйста, заполните все поля формы.');
        return;
      }
      
      // Конвертируем category_id в число
      const subcategoryData = {
        ...formData,
        category_id: Number(formData.category_id)
      };
      
      if (modalMode === 'add') {
        const response = await productAPI.createSubcategory(subcategoryData);
        setSubcategories([...subcategories, response.data]);
      } else {
        const response = await productAPI.updateSubcategory(selectedSubcategory.id, subcategoryData);
        setSubcategories(subcategories.map(sc => sc.id === selectedSubcategory.id ? response.data : sc));
      }
      setIsModalOpen(false);
    } catch (err) {
      console.error('Ошибка при сохранении подкатегории:', err);
      alert(`Не удалось сохранить подкатегорию: ${err.message || 'Проверьте введенные данные и права доступа.'}`);
    }
  };

  // Удаление подкатегории
  const handleDeleteSubcategory = async (subcategoryId) => {
    if (window.confirm('Вы уверены, что хотите удалить эту подкатегорию? Это также может удалить связанные товары.')) {
      try {
        await productAPI.deleteSubcategory(subcategoryId);
        setSubcategories(subcategories.filter(subcategory => subcategory.id !== subcategoryId));
      } catch (err) {
        console.error('Ошибка при удалении подкатегории:', err);
        alert('Не удалось удалить подкатегорию. Возможно, она используется в товарах.');
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
        <h2>Управление подкатегориями</h2>
        <button 
          className="btn btn-primary" 
          onClick={handleAddSubcategory}
        >
          <i className="bi bi-plus-circle me-2"></i>
          Добавить подкатегорию
        </button>
      </div>

      {subcategories.length === 0 ? (
        <div className="alert alert-info">
          Подкатегории отсутствуют. Добавьте новую подкатегорию, нажав на кнопку выше.
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-striped table-hover">
            <thead className="table-primary">
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Slug</th>
                <th>Категория</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {subcategories.map(subcategory => (
                <tr key={subcategory.id}>
                  <td>{subcategory.id}</td>
                  <td>{subcategory.name}</td>
                  <td>{subcategory.slug}</td>
                  <td>{getCategoryName(subcategory.category_id)}</td>
                  <td>
                    <button 
                      className="btn btn-sm btn-outline-primary me-2" 
                      onClick={() => handleEditSubcategory(subcategory)}
                    >
                      <i className="bi bi-pencil"></i>
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-danger" 
                      onClick={() => handleDeleteSubcategory(subcategory.id)}
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

      {/* Модальное окно для добавления/редактирования подкатегории */}
      {isModalOpen && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {modalMode === 'add' ? 'Добавить новую подкатегорию' : 'Редактировать подкатегорию'}
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
                    <label htmlFor="category_id" className="form-label">Категория</label>
                    <select
                      className="form-select"
                      id="category_id"
                      name="category_id"
                      value={formData.category_id}
                      onChange={handleInputChange}
                      required
                    >
                      <option value="">Выберите категорию</option>
                      {categories.map(category => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </div>
                
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
                  onClick={handleSaveSubcategory}
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

export default AdminSubcategories; 