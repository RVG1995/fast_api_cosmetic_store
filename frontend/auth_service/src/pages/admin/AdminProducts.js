import React, { useState, useEffect } from 'react';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProducts.css';

const AdminProducts = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('add'); // 'add' или 'edit'
  const [formData, setFormData] = useState({
    name: '',
    price: '',
    description: '',
    stock: '',
    category_id: '',  // Добавляем поле category_id в formData
    subcategory_id: '',
    country_id: '',
    brand_id: '',
    image: ''
  });
  
  // Добавляем состояние для предварительного просмотра изображения
  const [imagePreview, setImagePreview] = useState('');
  
  const [categories, setCategories] = useState([]);
  const [subcategories, setSubcategories] = useState([]); // Добавляем состояние для подкатегорий
  const [countries, setCountries] = useState([]);
  const [brands, setBrands] = useState([]);
  // Состояние для хранения отфильтрованных подкатегорий по выбранной категории
  const [filteredSubcategories, setFilteredSubcategories] = useState([]);

  // Загрузка всех необходимых данных при монтировании компонента
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Параллельная загрузка всех необходимых данных
        const [productsRes, categoriesRes, subcategoriesRes, countriesRes, brandsRes] = await Promise.all([
          productAPI.getProducts(),
          productAPI.getCategories(),
          productAPI.getSubcategories(), // Добавляем запрос подкатегорий
          productAPI.getCountries(),
          productAPI.getBrands()
        ]);
        
        // Добавляем логирование для отладки
        console.log('Полученные продукты:', productsRes.data);
        
        setProducts(productsRes.data);
        setCategories(categoriesRes.data);
        setSubcategories(subcategoriesRes.data); // Сохраняем подкатегории
        setCountries(countriesRes.data);
        setBrands(brandsRes.data);
        
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

  // Обновляем фильтрованные подкатегории при изменении категории
  useEffect(() => {
    console.log('Изменено значение category_id:', formData.category_id);
    
    if (formData.category_id) {
      const filtered = subcategories.filter(
        subcategory => subcategory.category_id === Number(formData.category_id)
      );
      console.log('Отфильтрованные подкатегории:', filtered);
      setFilteredSubcategories(filtered);
    } else {
      console.log('Категория не выбрана, фильтрация подкатегорий не выполняется');
      setFilteredSubcategories([]);
    }
  }, [formData.category_id, subcategories]);

  // Получаем названия категорий для отображения в подкатегориях
  const getCategoryName = React.useCallback((category_id) => {
    const category = categories.find(cat => cat.id === category_id);
    return category ? category.name : '';
  }, [categories]);

  // Обработчик изменения полей формы
  const handleInputChange = (e) => {
    const { name, value, type, files } = e.target;
    
    // Если это поле загрузки файла
    if (type === 'file') {
      if (files && files.length > 0) {
        // Сохраняем файл в formData
        setFormData({
          ...formData,
          [name]: files[0]
        });
        
        // Создаем URL для предварительного просмотра
        const fileUrl = URL.createObjectURL(files[0]);
        setImagePreview(fileUrl);
      }
    } else if (type === 'number') {
      // Для числовых полей преобразуем строку в число
      const numberValue = value === '' ? '' : Number(value);
      setFormData({
        ...formData,
        [name]: numberValue
      });
    } else {
      // Для остальных полей обрабатываем как раньше
      setFormData({
        ...formData,
        [name]: value
      });
      
      // Если изменилась категория, сбрасываем значение подкатегории
      if (name === 'category_id') {
        console.log('Изменена категория на:', value);
        setFormData(prev => {
          console.log('Обновление formData после изменения категории:', {
            ...prev,
            category_id: value,
            subcategory_id: ''
          });
          return {
            ...prev,
            [name]: value,
            subcategory_id: ''
          };
        });
      }
    }
  };

  // Открытие модального окна для добавления нового товара
  const handleAddProduct = () => {
    setModalMode('add');
    setFormData({
      name: '',
      price: '',
      description: '',
      stock: '',
      category_id: '',
      subcategory_id: '',
      country_id: '',
      brand_id: '',
      image: ''
    });
    setImagePreview('');
    setIsModalOpen(true);
  };

  // Открытие модального окна для редактирования товара
  const handleEditProduct = (product) => {
    setModalMode('edit');
    setSelectedProduct(product);
    
    // Отладочный вывод
    console.log('Исходные данные товара для редактирования:', product);
    
    // Получаем category_id из самого товара или определяем по подкатегории, если нет
    let categoryId = product.category_id ? String(product.category_id) : '';
    
    // Если категория не указана напрямую, но есть подкатегория, попробуем определить категорию
    if (!categoryId && product.subcategory_id) {
      const subcategory = subcategories.find(sub => sub.id === product.subcategory_id);
      if (subcategory) {
        categoryId = String(subcategory.category_id);
      }
    }
    
    console.log('Редактирование товара:', product);
    console.log('Выбранная категория:', categoryId);
    
    // Преобразуем числовые значения в строки для полей формы
    const formDataValues = {
      name: product.name,
      price: product.price,
      description: product.description || '',
      stock: product.stock,
      category_id: categoryId,
      subcategory_id: product.subcategory_id ? String(product.subcategory_id) : '',
      country_id: product.country_id ? String(product.country_id) : '',
      brand_id: product.brand_id ? String(product.brand_id) : '',
      image: product.image || ''
    };
    
    console.log('Установка formData для редактирования:', formDataValues);
    setFormData(formDataValues);
    
    // Если есть существующее изображение, устанавливаем его как предпросмотр
    setImagePreview(product.image ? `http://localhost:8001${product.image}` : '');
    setIsModalOpen(true);
  };

  // Сохранение товара (добавление или обновление)
  const handleSaveProduct = async () => {
    try {
      // Проверяем, что все необходимые поля заполнены
      const requiredFields = ['name', 'price', 'stock', 'country_id', 'brand_id', 'category_id']; // Добавляем category_id в обязательные поля
      const missingFields = requiredFields.filter(field => 
        formData[field] === '' || formData[field] === undefined
      );
      
      if (missingFields.length > 0) {
        alert(`Пожалуйста, заполните следующие обязательные поля: ${missingFields.join(', ')}`);
        return;
      }
      
      // Создаем копию formData для преобразования значений
      const processedData = { ...formData };
      
      // Обрабатываем числовые поля
      if (processedData.price !== '') processedData.price = Number(processedData.price);
      if (processedData.stock !== '') processedData.stock = Number(processedData.stock);
      if (processedData.category_id !== '') processedData.category_id = Number(processedData.category_id);
      if (processedData.subcategory_id !== '') processedData.subcategory_id = Number(processedData.subcategory_id);
      if (processedData.country_id !== '') processedData.country_id = Number(processedData.country_id);
      if (processedData.brand_id !== '') processedData.brand_id = Number(processedData.brand_id);
      
      console.log('Отправляем данные:', processedData);
      
      if (modalMode === 'add') {
        const response = await productAPI.createProduct(processedData);
        setProducts([...products, response.data]);
      } else {
        const response = await productAPI.updateProduct(selectedProduct.id, processedData);
        setProducts(products.map(p => p.id === selectedProduct.id ? response.data : p));
      }
      setIsModalOpen(false);
    } catch (err) {
      console.error('Ошибка при сохранении товара:', err);
      alert(`Не удалось сохранить товар: ${err.message || 'Проверьте введенные данные и права доступа.'}`);
    }
  };

  // Удаление товара
  const handleDeleteProduct = async (productId) => {
    if (window.confirm('Вы уверены, что хотите удалить этот товар?')) {
      try {
        await productAPI.deleteProduct(productId);
        setProducts(products.filter(product => product.id !== productId));
      } catch (err) {
        console.error('Ошибка при удалении товара:', err);
        alert('Не удалось удалить товар. Проверьте права доступа.');
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
        <h2>Управление товарами</h2>
        <button 
          className="btn btn-primary" 
          onClick={handleAddProduct}
        >
          <i className="bi bi-plus-circle me-2"></i>
          Добавить товар
        </button>
      </div>

      {products.length === 0 ? (
        <div className="alert alert-info">
          Товары отсутствуют. Добавьте новый товар, нажав на кнопку выше.
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-striped table-hover">
            <thead className="table-primary">
              <tr>
                <th>ID</th>
                <th>Изображение</th>
                <th>Название</th>
                <th>Цена</th>
                <th>Кол-во</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {products.map(product => (
                <tr key={product.id}>
                  <td>{product.id}</td>
                  <td>
                    {product.image ? (
                      <img 
                        src={`http://localhost:8001${product.image}`} 
                        alt={product.name} 
                        className="product-thumbnail" 
                      />
                    ) : (
                      <span className="no-image-small">Нет фото</span>
                    )}
                  </td>
                  <td>{product.name}</td>
                  <td>{product.price} руб.</td>
                  <td>{product.stock}</td>
                  <td>
                    <button 
                      className="btn btn-sm btn-outline-primary me-2" 
                      onClick={() => handleEditProduct(product)}
                    >
                      <i className="bi bi-pencil"></i>
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-danger" 
                      onClick={() => handleDeleteProduct(product.id)}
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

      {/* Модальное окно для добавления/редактирования товара */}
      {isModalOpen && (
        <div className="modal show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {modalMode === 'add' ? 'Добавить новый товар' : 'Редактировать товар'}
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
                  
                  <div className="row">
                    <div className="col-md-6 mb-3">
                      <label htmlFor="price" className="form-label">Цена</label>
                      <input
                        type="number"
                        className="form-control"
                        id="price"
                        name="price"
                        value={formData.price}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                    <div className="col-md-6 mb-3">
                      <label htmlFor="stock" className="form-label">Количество</label>
                      <input
                        type="number"
                        className="form-control"
                        id="stock"
                        name="stock"
                        value={formData.stock}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                  </div>
                  
                  <div className="mb-3">
                    <label htmlFor="description" className="form-label">Описание</label>
                    <textarea
                      className="form-control"
                      id="description"
                      name="description"
                      value={formData.description}
                      onChange={handleInputChange}
                      rows="3"
                    ></textarea>
                  </div>
                  
                  <div className="row">
                    <div className="col-md-4 mb-3">
                      <label htmlFor="brand_id" className="form-label">Бренд</label>
                      <select
                        className="form-select"
                        id="brand_id"
                        name="brand_id"
                        value={formData.brand_id}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">Выберите бренд</option>
                        {brands.map(brand => (
                          <option key={brand.id} value={brand.id}>
                            {brand.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-4 mb-3">
                      <label htmlFor="country_id" className="form-label">Страна</label>
                      <select
                        className="form-select"
                        id="country_id"
                        name="country_id"
                        value={formData.country_id}
                        onChange={handleInputChange}
                        required
                      >
                        <option value="">Выберите страну</option>
                        {countries.map(country => (
                          <option key={country.id} value={country.id}>
                            {country.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  
                  <div className="row">
                    {/* Добавляем поле выбора категории */}
                    <div className="col-md-6 mb-3">
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
                        {categories.map(category => {
                          console.log(`Отрисовка опции категории: id=${category.id}, name=${category.name}, selected=${formData.category_id === category.id}`);
                          return (
                            <option key={category.id} value={category.id}>
                              {category.name}
                            </option>
                          );
                        })}
                      </select>
                    </div>
                    <div className="col-md-6 mb-3">
                      <label htmlFor="subcategory_id" className="form-label">Подкатегория (необязательно)</label>
                      <select
                        className="form-select"
                        id="subcategory_id"
                        name="subcategory_id"
                        value={formData.subcategory_id}
                        onChange={handleInputChange}
                      >
                        <option value="">Выберите подкатегорию</option>
                        {formData.category_id ? (
                          filteredSubcategories.map(subcategory => (
                            <option key={subcategory.id} value={subcategory.id}>
                              {subcategory.name}
                            </option>
                          ))
                        ) : (
                          subcategories.map(subcategory => (
                            <option key={subcategory.id} value={subcategory.id}>
                              {subcategory.name} ({getCategoryName(subcategory.category_id)})
                            </option>
                          ))
                        )}
                      </select>
                    </div>
                  </div>
                  
                  <div className="mb-3">
                    <label htmlFor="image" className="form-label">Изображение</label>
                    <input
                      type="file"
                      className="form-control"
                      id="image"
                      name="image"
                      accept="image/*"
                      onChange={handleInputChange}
                    />
                    {imagePreview && (
                      <div className="mt-2">
                        <img 
                          src={imagePreview} 
                          alt="Предпросмотр" 
                          className="img-thumbnail" 
                          style={{ maxWidth: '200px', maxHeight: '200px' }}
                        />
                      </div>
                    )}
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
                  onClick={handleSaveProduct}
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

export default AdminProducts; 