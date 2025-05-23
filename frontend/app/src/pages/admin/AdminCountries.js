import React, { useState, useEffect } from 'react';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProducts.css'; // Используем те же стили, что и для товаров
// Импорты react-bootstrap и axios удалены, так как не используются в компоненте
import { generateSlug } from '../../utils/slugUtils';
import { useConfirm } from '../../components/common/ConfirmContext';

const AdminCountries = () => {
  const confirm = useConfirm();
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('add'); // 'add' или 'edit'
  const [formData, setFormData] = useState({
    name: '',
    slug: ''
  });

  // Загрузка стран при монтировании компонента
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await productAPI.getCountries();
        setCountries(response.data);
        setError(null);
      } catch (err) {
        console.error('Ошибка при загрузке стран:', err);
        setError('Не удалось загрузить страны. Пожалуйста, попробуйте позже.');
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
      const slug = generateSlug(value);
      
      setFormData(prev => ({
        ...prev,
        slug
      }));
    }
  };

  // Открытие модального окна для добавления новой страны
  const handleAddCountry = () => {
    setModalMode('add');
    setFormData({
      name: '',
      slug: ''
    });
    setIsModalOpen(true);
  };

  // Открытие модального окна для редактирования страны
  const handleEditCountry = (country) => {
    setModalMode('edit');
    setSelectedCountry(country);
    setFormData({
      name: country.name,
      slug: country.slug
    });
    setIsModalOpen(true);
  };

  // Сохранение страны (добавление или обновление)
  const handleSaveCountry = async () => {
    try {
      // Проверяем, что все необходимые поля заполнены
      if (!formData.name || !formData.slug) {
        alert('Пожалуйста, заполните все поля формы.');
        return;
      }
      
      if (modalMode === 'add') {
        const response = await productAPI.createCountry(formData);
        setCountries([...countries, response.data]);
      } else {
        const response = await productAPI.updateCountry(selectedCountry.id, formData);
        setCountries(countries.map(c => c.id === selectedCountry.id ? response.data : c));
      }
      setIsModalOpen(false);
    } catch (err) {
      console.error('Ошибка при сохранении страны:', err);
      alert(`Не удалось сохранить страну: ${err.message || 'Проверьте введенные данные и права доступа.'}`);
    }
  };

  // Удаление страны
  const handleDeleteCountry = async (countryId) => {
    const ok = await confirm({
      title: 'Удалить страну?',
      body: 'Это также может удалить связанные товары. Продолжить?'
    });
    if (!ok) return;
    try {
      await productAPI.deleteCountry(countryId);
      setCountries(countries.filter(country => country.id !== countryId));
    } catch (err) {
      console.error('Ошибка при удалении страны:', err);
      alert('Не удалось удалить страну. Возможно, она используется в товарах.');
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
        <h2>Управление странами</h2>
        <button 
          className="btn btn-primary" 
          onClick={handleAddCountry}
        >
          <i className="bi bi-plus-circle me-2"></i>
          Добавить страну
        </button>
      </div>

      {countries.length === 0 ? (
        <div className="alert alert-info">
          Страны отсутствуют. Добавьте новую страну, нажав на кнопку выше.
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
              {countries.map(country => (
                <tr key={country.id}>
                  <td>{country.id}</td>
                  <td>{country.name}</td>
                  <td>{country.slug}</td>
                  <td>
                    <button 
                      className="btn btn-sm btn-outline-primary me-2" 
                      onClick={() => handleEditCountry(country)}
                    >
                      <i className="bi bi-pencil"></i>
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-danger" 
                      onClick={() => handleDeleteCountry(country.id)}
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

      {/* Модальное окно для добавления/редактирования страны */}
      {isModalOpen && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {modalMode === 'add' ? 'Добавить новую страну' : 'Редактировать страну'}
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
                  onClick={handleSaveCountry}
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

export default AdminCountries; 