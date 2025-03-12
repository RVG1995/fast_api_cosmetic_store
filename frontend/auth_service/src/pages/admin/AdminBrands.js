import React, { useState, useEffect } from 'react';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProducts.css'; // Используем те же стили, что и для товаров

const AdminBrands = () => {
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('add'); // 'add' или 'edit'
  const [formData, setFormData] = useState({
    name: '',
    slug: ''
  });

  // Загрузка брендов при монтировании компонента
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await productAPI.getBrands();
        setBrands(response.data);
        setError(null);
      } catch (err) {
        console.error('Ошибка при загрузке брендов:', err);
        setError('Не удалось загрузить бренды. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Обработчик изменения полей формы
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
    
    // Если изменилось имя, автоматически генерируем slug
    if (name === 'name') {
      const slug = value
        .toLowerCase()
        .replace(/[^\w\s-]/g, '') // Удаляем спецсимволы
        .replace(/[\s_-]+/g, '-') // Заменяем пробелы и подчеркивания на дефисы
        .replace(/^-+|-+$/g, ''); // Удаляем дефисы в начале и конце строки
      
      setFormData(prev => ({
        ...prev,
        slug
      }));
    }
  };

  // Открытие модального окна для добавления нового бренда
  const handleAddBrand = () => {
    setModalMode('add');
    setFormData({
      name: '',
      slug: ''
    });
    setIsModalOpen(true);
  };

  // Открытие модального окна для редактирования бренда
  const handleEditBrand = (brand) => {
    setModalMode('edit');
    setSelectedBrand(brand);
    setFormData({
      name: brand.name,
      slug: brand.slug
    });
    setIsModalOpen(true);
  };

  // Сохранение бренда (добавление или обновление)
  const handleSaveBrand = async () => {
    try {
      // Проверяем, что все необходимые поля заполнены
      if (!formData.name || !formData.slug) {
        alert('Пожалуйста, заполните все поля формы.');
        return;
      }
      
      if (modalMode === 'add') {
        const response = await productAPI.createBrand(formData);
        setBrands([...brands, response.data]);
      } else {
        const response = await productAPI.updateBrand(selectedBrand.id, formData);
        setBrands(brands.map(b => b.id === selectedBrand.id ? response.data : b));
      }
      setIsModalOpen(false);
    } catch (err) {
      console.error('Ошибка при сохранении бренда:', err);
      alert(`Не удалось сохранить бренд: ${err.message || 'Проверьте введенные данные и права доступа.'}`);
    }
  };

  // Удаление бренда
  const handleDeleteBrand = async (brandId) => {
    if (window.confirm('Вы уверены, что хотите удалить этот бренд? Это также может удалить связанные товары.')) {
      try {
        await productAPI.deleteBrand(brandId);
        setBrands(brands.filter(brand => brand.id !== brandId));
      } catch (err) {
        console.error('Ошибка при удалении бренда:', err);
        alert('Не удалось удалить бренд. Возможно, он используется в товарах.');
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
        <h2>Управление брендами</h2>
        <button 
          className="btn btn-primary" 
          onClick={handleAddBrand}
        >
          <i className="bi bi-plus-circle me-2"></i>
          Добавить бренд
        </button>
      </div>

      {brands.length === 0 ? (
        <div className="alert alert-info">
          Бренды отсутствуют. Добавьте новый бренд, нажав на кнопку выше.
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
              {brands.map(brand => (
                <tr key={brand.id}>
                  <td>{brand.id}</td>
                  <td>{brand.name}</td>
                  <td>{brand.slug}</td>
                  <td>
                    <button 
                      className="btn btn-sm btn-outline-primary me-2" 
                      onClick={() => handleEditBrand(brand)}
                    >
                      <i className="bi bi-pencil"></i>
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-danger" 
                      onClick={() => handleDeleteBrand(brand.id)}
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

      {/* Модальное окно для добавления/редактирования бренда */}
      {isModalOpen && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {modalMode === 'add' ? 'Добавить новый бренд' : 'Редактировать бренд'}
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
                  onClick={handleSaveBrand}
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

export default AdminBrands; 