import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { productAPI } from '../../utils/api';
import '../../styles/AdminProductDetail.css';
import ReviewList from '../../components/reviews/ReviewList';
import { useConfirm } from '../../components/common/ConfirmContext';

const AdminProductDetail = () => {
  const confirm = useConfirm();
  const { productId } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Дополнительные состояния для связанных данных
  const [category, setCategory] = useState(null);
  const [subcategory, setSubcategory] = useState(null);
  const [country, setCountry] = useState(null);
  const [brand, setBrand] = useState(null);

  // Состояния для модального окна редактирования
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
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
  const [imagePreview, setImagePreview] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  
  // Состояния для списков
  const [categories, setCategories] = useState([]);
  const [subcategories, setSubcategories] = useState([]);
  const [countries, setCountries] = useState([]);
  const [brands, setBrands] = useState([]);
  const [filteredSubcategories, setFilteredSubcategories] = useState([]);

  // Загрузка данных о товаре
  useEffect(() => {
    const fetchProductData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Получаем данные о товаре
        const response = await productAPI.getProductById(productId);
        
        // Проверяем, что данные получены
        if (!response.data) {
          setError('Товар не найден');
          setLoading(false);
          return;
        }
        
        const productData = response.data;
        setProduct(productData);
        
        // Загружаем все необходимые данные для формы
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
        
        // Используем уже имеющуюся информацию о связанных данных из ответа API
        if (productData.category) {
          setCategory(productData.category);
        }
        
        if (productData.subcategory) {
          setSubcategory(productData.subcategory);
        }
        
        if (productData.country) {
          setCountry(productData.country);
        }
        
        if (productData.brand) {
          setBrand(productData.brand);
        }
      } catch (err) {
        console.error('Ошибка при загрузке данных о товаре:', err);
        
        // Определяем тип ошибки
        if (err.response && err.response.status === 404) {
          setError('Товар не найден');
        } else {
          setError('Не удалось загрузить данные о товаре');
        }
      } finally {
        setLoading(false);
      }
    };
    
    if (productId) {
      fetchProductData();
    }
  }, [productId]);

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

  // Обработчик редактирования товара
  const handleEdit = () => {
    if (product) {
      // Заполняем форму данными товара
      setFormData({
        name: product.name,
        price: product.price,
        description: product.description || '',
        stock: product.stock,
        category_id: product.category_id ? String(product.category_id) : '',
        subcategory_id: product.subcategory_id ? String(product.subcategory_id) : '',
        country_id: product.country_id ? String(product.country_id) : '',
        brand_id: product.brand_id ? String(product.brand_id) : '',
        image: product.image || ''
      });
      
      // Устанавливаем предпросмотр изображения
      setImagePreview(product.image ? `http://localhost:8001${product.image}` : '');
      
      // Открываем модальное окно редактирования
      setIsModalOpen(true);
    }
  };

  // Обработчик изменения полей формы
  const handleInputChange = (e) => {
    const { name, value, type, files } = e.target;
    
    // Если это поле загрузки файла
    if (type === 'file') {
      if (files && files.length > 0) {
        // Сохраняем файл в selectedFile
        setSelectedFile(files[0]);
        
        // Создаем URL для предпросмотра изображения
        const previewURL = URL.createObjectURL(files[0]);
        setImagePreview(previewURL);
        
        // Обновляем formData
        setFormData({
          ...formData,
          image: files[0].name // Для отображения в форме
        });
      }
    }
    // Если это числовое поле (price, stock)
    else if (name === 'price' || name === 'stock') {
      // Преобразуем в число или оставляем пустую строку
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

  // Обработчик сохранения изменений товара
  const handleSaveProduct = async (e) => {
    e.preventDefault();
    
    try {
      // Создаем объект с данными товара
      const productData = {
        name: formData.name,
        price: formData.price,
        description: formData.description,
        stock: formData.stock,
        category_id: formData.category_id,
        subcategory_id: formData.subcategory_id || null,
        country_id: formData.country_id,
        brand_id: formData.brand_id
      };
      
      // Если был выбран новый файл изображения, добавляем его в объект данных
      if (selectedFile) {
        productData.image = selectedFile;
      }
      
      // Отправляем запрос на обновление товара
      const response = await productAPI.updateProduct(productId, productData);
      
      // Обновляем данные товара на странице
      setProduct(response.data);
      
      // Обновляем также связанные данные
      if (response.data.category_id) {
        try {
          const categoryResponse = await productAPI.getCategoryById(response.data.category_id);
          setCategory(categoryResponse.data);
        } catch (err) {
          console.error('Ошибка при загрузке обновленной категории:', err);
        }
      }
      
      if (response.data.subcategory_id) {
        try {
          const subcategoryResponse = await productAPI.getSubcategoryById(response.data.subcategory_id);
          setSubcategory(subcategoryResponse.data);
        } catch (err) {
          console.error('Ошибка при загрузке обновленной подкатегории:', err);
        }
      } else {
        setSubcategory(null);
      }
      
      if (response.data.country_id) {
        try {
          const countryResponse = await productAPI.getCountryById(response.data.country_id);
          setCountry(countryResponse.data);
        } catch (err) {
          console.error('Ошибка при загрузке обновленной страны:', err);
        }
      }
      
      if (response.data.brand_id) {
        try {
          const brandResponse = await productAPI.getBrandById(response.data.brand_id);
          setBrand(brandResponse.data);
        } catch (err) {
          console.error('Ошибка при загрузке обновленного бренда:', err);
        }
      }
      
      // Закрываем модальное окно
      setIsModalOpen(false);
      
      // Сбрасываем состояние выбранного файла
      setSelectedFile(null);
      
    } catch (err) {
      console.error('Ошибка при обновлении товара:', err);
      setError('Не удалось обновить товар. Пожалуйста, попробуйте позже.');
    }
  };

  // Обработчик закрытия модального окна
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedFile(null);
  };

  // Обработчик удаления товара
  const handleDelete = async () => {
    const ok = await confirm({
      title: 'Удалить товар?',
      body: 'Вы действительно хотите удалить этот товар?'
    });
    if (!ok) return;
    try {
      await productAPI.deleteProduct(productId);
      navigate('/admin/products', { 
        state: { 
          notification: {
            type: 'success',
            message: 'Товар успешно удален'
          }
        }
      });
    } catch (err) {
      console.error('Ошибка при удалении товара:', err);
      setError('Не удалось удалить товар. Пожалуйста, попробуйте позже.');
    }
  };

  if (loading) {
    return (
      <div className="admin-product-detail container py-4">
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
          <p className="mt-2">Загрузка информации о товаре...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-product-detail container py-4">
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Ошибка</h4>
          <p>{error}</p>
          <p>Возможно, товар был удален или перемещен.</p>
        </div>
        <Link to="/admin/products" className="btn btn-primary">
          Вернуться к списку товаров
        </Link>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="admin-product-detail container py-4">
        <div className="alert alert-warning" role="alert">
          <h4 className="alert-heading">Товар не найден</h4>
          <p>Запрашиваемый товар не существует или был удален.</p>
        </div>
        <Link to="/admin/products" className="btn btn-primary">
          Вернуться к списку товаров
        </Link>
      </div>
    );
  }

  return (
    <div className="admin-product-detail container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Информация о товаре</h2>
        <div>
          <button 
            className="btn btn-primary me-2"
            onClick={handleEdit}
          >
            <i className="bi bi-pencil me-1"></i>
            Редактировать
          </button>
          <button 
            className="btn btn-danger"
            onClick={handleDelete}
          >
            <i className="bi bi-trash me-1"></i>
            Удалить
          </button>
          <Link
            to="/admin/products"
            className="btn btn-outline-secondary ms-2"
          >
            <i className="bi bi-arrow-left me-1"></i>
            Назад к списку
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
          <p className="mt-2">Загрузка информации о товаре...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Ошибка</h4>
          <p>{error}</p>
          <p>Возможно, товар был удален или перемещен.</p>
        </div>
      ) : !product ? (
        <div className="alert alert-warning" role="alert">
          <h4 className="alert-heading">Товар не найден</h4>
          <p>Запрашиваемый товар не существует или был удален.</p>
        </div>
      ) : (
        <>
          <div className="card">
            <div className="row g-0">
              <div className="col-md-4 product-image-container">
                {product.image ? (
                  <img 
                    src={`http://localhost:8001${product.image}`} 
                    alt={product.name} 
                    className="product-detail-image"
                  />
                ) : (
                  <div className="no-image-large">
                    <i className="bi bi-image"></i>
                    <span>Изображение отсутствует</span>
                  </div>
                )}
              </div>
              <div className="col-md-8">
                <div className="card-body">
                  <h3 className="card-title">{product.name}</h3>
                  
                  <div className="product-meta">
                    <div className="product-id text-muted">
                      ID товара: {product.id}
                    </div>
                    <div className="product-price">
                      Цена: <strong>{product.price} ₽</strong>
                    </div>
                    <div className="product-stock">
                      Наличие: 
                      <span className={`badge ms-2 ${product.stock > 0 ? 'bg-success' : 'bg-danger'}`}>
                        {product.stock > 0 ? `В наличии (${product.stock} шт.)` : 'Нет в наличии'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="product-attributes">
                    <table className="table table-borderless">
                      <tbody>
                        <tr>
                          <th scope="row" style={{width: "150px"}}>Категория:</th>
                          <td>
                            {category ? (
                              <Link to={`/admin/categories?edit=${category.id}`}>
                                {category.name}
                              </Link>
                            ) : (
                              <span className="text-muted">Не указана</span>
                            )}
                          </td>
                        </tr>
                        <tr>
                          <th scope="row">Подкатегория:</th>
                          <td>
                            {subcategory ? (
                              <Link to={`/admin/subcategories?edit=${subcategory.id}`}>
                                {subcategory.name}
                              </Link>
                            ) : (
                              <span className="text-muted">Не указана</span>
                            )}
                          </td>
                        </tr>
                        <tr>
                          <th scope="row">Бренд:</th>
                          <td>
                            {brand ? (
                              <Link to={`/admin/brands?edit=${brand.id}`}>
                                {brand.name}
                              </Link>
                            ) : (
                              <span className="text-muted">Не указан</span>
                            )}
                          </td>
                        </tr>
                        <tr>
                          <th scope="row">Страна:</th>
                          <td>
                            {country ? (
                              <Link to={`/admin/countries?edit=${country.id}`}>
                                {country.name}
                              </Link>
                            ) : (
                              <span className="text-muted">Не указана</span>
                            )}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  
                  <div className="product-description">
                    <h5>Описание</h5>
                    <p>{product.description || <span className="text-muted">Описание отсутствует</span>}</p>
                  </div>
                  
                  <div className="product-timestamps text-muted">
                    <p>
                      Создан: {product.created_at ? new Date(product.created_at).toLocaleString() : 'Неизвестно'}
                      <br />
                      Последнее обновление: {product.updated_at ? new Date(product.updated_at).toLocaleString() : 'Неизвестно'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        
          {/* Добавляем блок с отзывами */}
          <div className="card">
            <div className="card-header">
              <h3>Отзывы о товаре</h3>
            </div>
            <div className="card-body">
              <ReviewList 
                productId={productId} 
                isAdminView={true}
              />
            </div>
          </div>
        
          {/* Модальное окно редактирования товара */}
          <div className={`modal fade ${isModalOpen ? 'show' : ''}`} 
            style={{ display: isModalOpen ? 'block' : 'none' }} 
            tabIndex="-1" 
            role="dialog"
            aria-hidden={!isModalOpen}
          >
            <div className="modal-dialog modal-lg">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">Редактирование товара</h5>
                  <button 
                    type="button" 
                    className="btn-close" 
                    onClick={handleCloseModal}
                    aria-label="Close"
                  ></button>
                </div>
                <div className="modal-body">
                  <form id="productForm" onSubmit={handleSaveProduct}>
                    <div className="row">
                      <div className="col-md-8">
                        <div className="mb-3">
                          <label htmlFor="name" className="form-label">Название товара</label>
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
                      </div>
                      <div className="col-md-4">
                        <div className="mb-3">
                          <label htmlFor="price" className="form-label">Цена (руб.)</label>
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
                      </div>
                    </div>
                    
                    <div className="row">
                      <div className="col-md-4">
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
                      </div>
                      <div className="col-md-4">
                        <div className="mb-3">
                          <label htmlFor="subcategory_id" className="form-label">Подкатегория</label>
                          <select 
                            className="form-select" 
                            id="subcategory_id" 
                            name="subcategory_id"
                            value={formData.subcategory_id}
                            onChange={handleInputChange}
                          >
                            <option value="">Выберите подкатегорию</option>
                            {filteredSubcategories.map(subcategory => (
                              <option key={subcategory.id} value={subcategory.id}>
                                {subcategory.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div className="col-md-4">
                        <div className="mb-3">
                          <label htmlFor="stock" className="form-label">Количество на складе</label>
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
                      <div className="col-md-6">
                        <div className="mb-3">
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
                      <div className="col-md-6">
                        <div className="mb-3">
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
                      </div>
                    </div>
                    
                    <div className="mb-3">
                      <label htmlFor="image" className="form-label">Изображение товара</label>
                      <input 
                        type="file" 
                        className="form-control" 
                        id="image" 
                        name="image"
                        onChange={handleInputChange}
                        accept="image/*"
                      />
                      {imagePreview && (
                        <div className="mt-2 text-center">
                          <p>Предпросмотр изображения:</p>
                          <img 
                            src={imagePreview} 
                            alt="Preview" 
                            style={{ maxHeight: '200px', maxWidth: '100%' }} 
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
                    onClick={handleCloseModal}
                  >
                    Отмена
                  </button>
                  <button 
                    type="submit" 
                    form="productForm"
                    className="btn btn-primary"
                  >
                    Сохранить изменения
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* Затемнение фона при открытии модального окна */}
          {isModalOpen && (
            <div 
              className="modal-backdrop fade show" 
              onClick={handleCloseModal}
            ></div>
          )}
        </>
      )}
      
      <Link to="/admin/products" className="btn btn-outline-secondary mt-3">
        <i className="bi bi-arrow-left me-1"></i>
        Назад к списку товаров
      </Link>
    </div>
  );
};

export default AdminProductDetail; 