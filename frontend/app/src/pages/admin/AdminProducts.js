import React, { useState, useEffect } from 'react';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProducts.css';
import { Link, useLocation, useNavigate } from 'react-router-dom';

const AdminProducts = () => {
  const location = useLocation();
  const navigate = useNavigate();
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
  // Добавляем состояние для хранения выбранного файла
  const [selectedFile, setSelectedFile] = useState(null);
  
  const [categories, setCategories] = useState([]);
  const [subcategories, setSubcategories] = useState([]); // Добавляем состояние для подкатегорий
  const [countries, setCountries] = useState([]);
  const [brands, setBrands] = useState([]);
  // Состояние для хранения отфильтрованных подкатегорий по выбранной категории
  const [filteredSubcategories, setFilteredSubcategories] = useState([]);

  // Добавляем состояние для пагинации
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    pageSize: 10
  });

  // Добавляем состояние для сортировки
  const [sortOption, setSortOption] = useState('newest');

  // Загрузка всех необходимых данных при монтировании компонента
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Получаем все необходимые данные для формы и первую страницу товаров
        const [categoriesRes, subcategoriesRes, countriesRes, brandsRes] = await Promise.all([
          productAPI.getCategories(),
          productAPI.getSubcategories(),
          productAPI.getCountries(),
          productAPI.getBrands()
        ]);
        
        setCategories(categoriesRes.data);
        setSubcategories(subcategoriesRes.data);
        setCountries(countriesRes.data);
        setBrands(brandsRes.data);
        
        // Загружаем первую страницу товаров
        await fetchProducts(1);
        
        // Проверяем параметр edit в URL
        const queryParams = new URLSearchParams(location.search);
        const editProductId = queryParams.get('edit');
        
        if (editProductId) {
          console.log(`Обнаружен параметр edit=${editProductId} в URL`);
          try {
            // Загружаем данные о товаре для редактирования
            const productResponse = await productAPI.getProductById(editProductId);
            if (productResponse.data) {
              // Открываем модальное окно редактирования
              handleEditProduct(productResponse.data);
              // Удаляем параметр из URL без перезагрузки страницы
              navigate('/admin/products', { replace: true });
            }
          } catch (err) {
            console.error('Ошибка при загрузке товара для редактирования:', err);
            setError('Не удалось загрузить товар для редактирования');
          }
        }
      } catch (err) {
        console.error('Ошибка при загрузке данных:', err);
        setError('Не удалось загрузить данные. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Добавляем эффект для обновления товаров при изменении сортировки
  useEffect(() => {
    console.log('Сортировка изменилась на:', sortOption);
    // Загружаем товары с новой сортировкой, но сохраняем текущую страницу
    fetchProducts(pagination.currentPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortOption]);

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
        // Сохраняем файл в selectedFile
        setSelectedFile(files[0]);
        
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
    setSelectedFile(null); // Сбрасываем выбранный файл
    setIsModalOpen(true);
  };

  // Открытие модального окна для редактирования товара
  const handleEditProduct = (product) => {
    setModalMode('edit');
    setSelectedProduct(product);
    setSelectedFile(null); // Сбрасываем выбранный файл
    
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

  // Функция для загрузки определенной страницы товаров
  const fetchProducts = async (page) => {
    try {
      setLoading(true);
      console.log(`Загружаем страницу ${page} с сортировкой ${sortOption}`);
      // Принудительно передаем параметр сортировки, даже если это 'newest'
      const response = await productAPI.getAdminProducts(page, pagination.pageSize, null, null, null, null, sortOption);
      
      // Обновляем товары и информацию о пагинации
      const { items, total, limit } = response.data;
      console.log(`Получено ${items?.length} товаров из ${total} с лимитом ${limit}`);
      
      // Проверяем первые товары для отладки
      if (items && items.length > 0) {
        console.log('Первые два товара:', items.slice(0, 2).map(item => ({
          id: item.id,
          name: item.name,
          price: item.price
        })));
      }
      
      setProducts(Array.isArray(items) ? items : []);
      
      // Обновляем информацию о пагинации
      setPagination({
        currentPage: page,
        totalPages: Math.ceil(total / limit),
        totalItems: total,
        pageSize: limit
      });
      
      setError(null);
    } catch (err) {
      console.error('Ошибка при загрузке товаров:', err);
      setError('Не удалось загрузить товары. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  // Обработчик изменения страницы
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      fetchProducts(newPage);
    }
  };

  // Компонент пагинации
  const Pagination = () => {
    if (pagination.totalPages <= 1) return null;
    
    return (
      <nav aria-label="Пагинация товаров" className="mt-4">
        <ul className="pagination justify-content-center">
          <li className={`page-item ${pagination.currentPage === 1 ? 'disabled' : ''}`}>
            <button 
              className="page-link" 
              onClick={() => handlePageChange(pagination.currentPage - 1)}
              disabled={pagination.currentPage === 1}
            >
              &laquo; Назад
            </button>
          </li>
          
          {/* Генерируем страницы для отображения */}
          {Array.from({ length: pagination.totalPages }, (_, i) => i + 1)
            .filter(page => 
              // Показываем первую, последнюю и страницы рядом с текущей
              page === 1 || 
              page === pagination.totalPages || 
              Math.abs(page - pagination.currentPage) <= 2
            )
            .map((page, index, array) => {
              // Добавляем многоточие перед первой страницей, если она не 1 или 2
              const prevPage = index > 0 ? array[index - 1] : null;
              const showEllipsisBefore = prevPage !== null && page - prevPage > 1;
              
              return (
                <React.Fragment key={page}>
                  {showEllipsisBefore && (
                    <li className="page-item disabled">
                      <span className="page-link">...</span>
                    </li>
                  )}
                  <li className={`page-item ${pagination.currentPage === page ? 'active' : ''}`}>
                    <button 
                      className="page-link" 
                      onClick={() => handlePageChange(page)}
                    >
                      {page}
                    </button>
                  </li>
                </React.Fragment>
              );
            })}
          
          <li className={`page-item ${pagination.currentPage === pagination.totalPages ? 'disabled' : ''}`}>
            <button 
              className="page-link" 
              onClick={() => handlePageChange(pagination.currentPage + 1)}
              disabled={pagination.currentPage === pagination.totalPages}
            >
              Вперед &raquo;
            </button>
          </li>
        </ul>
      </nav>
    );
  };

  // Сохранение товара (добавление или обновление)
  const handleSaveProduct = async (e) => {
    e.preventDefault();
    
    try {
      console.log('Сохраняем данные товара:', formData);
      
      // Копируем данные для обработки
      const processedData = { ...formData };
      
      // Если изображение выбрано, добавляем его в данные формы
      if (selectedFile) {
        processedData.image = selectedFile;
      }
      
      // Конвертация строк в числа для числовых полей
      if (processedData.price !== '') processedData.price = Number(processedData.price);
      if (processedData.stock !== '') processedData.stock = Number(processedData.stock);
      if (processedData.category_id !== '') processedData.category_id = Number(processedData.category_id);
      if (processedData.subcategory_id !== '') processedData.subcategory_id = Number(processedData.subcategory_id);
      if (processedData.country_id !== '') processedData.country_id = Number(processedData.country_id);
      if (processedData.brand_id !== '') processedData.brand_id = Number(processedData.brand_id);
      
      console.log('Отправляем данные:', processedData);
      
      if (modalMode === 'add') {
        await productAPI.createProduct(processedData);
        // После добавления нового товара, обновляем список
        fetchProducts(pagination.currentPage);
      } else {
        await productAPI.updateProduct(selectedProduct.id, processedData);
        // После обновления товара, обновляем список
        fetchProducts(pagination.currentPage);
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
        // После удаления обновляем список товаров
        fetchProducts(pagination.currentPage);
      } catch (err) {
        console.error('Ошибка при удалении товара:', err);
        alert('Не удалось удалить товар. Проверьте права доступа.');
      }
    }
  };

  // Обработчик изменения сортировки
  const handleSortChange = (e) => {
    const newSortOption = e.target.value;
    console.log(`Изменение сортировки с ${sortOption} на ${newSortOption}`);
    setSortOption(newSortOption);
    // fetchProducts(1) не нужен здесь, так как вызовется через useEffect
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
        <>
          <div className="d-flex justify-content-between mb-4">
            <div className="d-flex align-items-center">
              <label htmlFor="sortSelect" className="me-2">Сортировка по цене:</label>
              <select 
                id="sortSelect" 
                className="form-select" 
                value={sortOption} 
                onChange={handleSortChange}
              >
                <option value="newest">По умолчанию</option>
                <option value="price_asc">Цена (по возрастанию)</option>
                <option value="price_desc">Цена (по убыванию)</option>
              </select>
            </div>
          </div>
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
                        <Link to={`/admin/products/${product.id}`}>
                          <img 
                            src={`http://localhost:8001${product.image}`} 
                            alt={product.name} 
                            className="product-thumbnail" 
                          />
                        </Link>
                      ) : (
                        <span className="no-image-small">Нет фото</span>
                      )}
                    </td>
                    <td>
                      <Link to={`/admin/products/${product.id}`} className="product-name-link">
                        {product.name}
                      </Link>
                    </td>
                    <td>{product.price} руб.</td>
                    <td>{product.stock}</td>
                    <td>
                      <Link 
                        to={`/admin/products/${product.id}`}
                        className="btn btn-sm btn-outline-info me-1"
                        title="Просмотр"
                      >
                        <i className="bi bi-eye"></i> Просмотр
                      </Link>
                      <button 
                        className="btn btn-sm btn-outline-primary me-1" 
                        onClick={() => handleEditProduct(product)}
                        title="Редактировать"
                      >
                        <i className="bi bi-pencil"></i> Редактировать
                      </button>
                      <button 
                        className="btn btn-sm btn-outline-danger" 
                        onClick={() => handleDeleteProduct(product.id)}
                        title="Удалить"
                      >
                        <i className="bi bi-trash"></i> Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Добавляем пагинацию после таблицы */}
          <Pagination />
          
          {/* Отображаем информацию о пагинации */}
          <div className="pagination-info text-center mt-2">
            <p>
              Показано {products.length} из {pagination.totalItems} товаров 
              (Страница {pagination.currentPage} из {pagination.totalPages})
            </p>
          </div>
        </>
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