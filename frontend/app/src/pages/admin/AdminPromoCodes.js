import React, { useState, useEffect } from 'react';
import {
  Container, Row, Col, Table, Button, Form, Modal, Alert, Spinner,
  InputGroup, FormControl, Badge
} from 'react-bootstrap';
import { formatDateTime } from '../../utils/dateUtils';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';

const AdminPromoCodes = () => {
  // State для промокодов
  const [promoCodes, setPromoCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State для модальных окон
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  
  // State для текущего промокода
  const [currentPromoCode, setCurrentPromoCode] = useState(null);
  
  // State для формы создания/редактирования
  const [formData, setFormData] = useState({
    code: '',
    discount_percent: '',
    discount_amount: '',
    valid_until: '',
    is_active: true
  });
  
  // State для фильтрации и поиска
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  
  // State для уведомлений
  const [notification, setNotification] = useState({ show: false, message: '', variant: 'success' });
  
  // Форматирование даты для input type="datetime-local"
  const formatDateForInput = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDThh:mm
  };
  
  // Загрузка промокодов
  useEffect(() => {
    fetchPromoCodes();
  }, []);
  
  const fetchPromoCodes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URLS.ORDER_SERVICE}/admin/promo-codes`, {
        withCredentials: true
      });
      setPromoCodes(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching promo codes:', err);
      setError('Не удалось загрузить промокоды. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };
  
  // Обработчики формы
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };
  
  // Открытие модального окна создания промокода
  const handleShowCreateModal = () => {
    setFormData({
      code: '',
      discount_percent: '',
      discount_amount: '',
      valid_until: formatDateForInput(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)), // +30 дней
      is_active: true
    });
    setShowCreateModal(true);
  };
  
  // Открытие модального окна редактирования промокода
  const handleShowEditModal = (promoCode) => {
    setCurrentPromoCode(promoCode);
    setFormData({
      code: promoCode.code,
      discount_percent: promoCode.discount_percent || '',
      discount_amount: promoCode.discount_amount || '',
      valid_until: formatDateForInput(promoCode.valid_until),
      is_active: promoCode.is_active
    });
    setShowEditModal(true);
  };
  
  // Открытие модального окна удаления промокода
  const handleShowDeleteModal = (promoCode) => {
    setCurrentPromoCode(promoCode);
    setShowDeleteModal(true);
  };
  
  // Функция для отображения уведомлений
  const showNotification = (message, variant = 'success') => {
    setNotification({ show: true, message, variant });
    // Автоматически скрываем уведомление через 3 секунды
    setTimeout(() => {
      setNotification({ show: false, message: '', variant: 'success' });
    }, 3000);
    
    // Также отправляем событие для отображения уведомления в Layout
    const event = new CustomEvent('show:toast', {
      detail: { message, type: variant }
    });
    document.dispatchEvent(event);
  };
  
  // Создание промокода
  const handleCreatePromoCode = async () => {
    try {
      // Проверка, чтобы только одно из полей discount_percent или discount_amount было заполнено
      if ((formData.discount_percent && formData.discount_amount) || 
          (!formData.discount_percent && !formData.discount_amount)) {
        showNotification('Укажите только одно из полей: процент скидки или фиксированную сумму', 'danger');
        return;
      }
      
      // Создаем копию данных формы и преобразуем пустые строки в null для числовых полей
      const dataToSend = {
        ...formData,
        discount_percent: formData.discount_percent === '' ? null : 
                          formData.discount_percent ? parseInt(formData.discount_percent, 10) : null,
        discount_amount: formData.discount_amount === '' ? null : 
                        formData.discount_amount ? parseInt(formData.discount_amount, 10) : null
      };
      
      await axios.post(`${API_URLS.ORDER_SERVICE}/admin/promo-codes`, dataToSend, {
        withCredentials: true
      });
      
      showNotification('Промокод успешно создан');
      setShowCreateModal(false);
      fetchPromoCodes();
    } catch (err) {
      console.error('Error creating promo code:', err);
      
      // Улучшенная обработка ошибок валидации
      let errorMessage = 'Ошибка создания промокода';
      
      if (err.response?.data) {
        // Обработка ошибок валидации из Pydantic
        if (err.response.data.detail && Array.isArray(err.response.data.detail)) {
          // Берем первую ошибку из списка ошибок валидации
          const firstError = err.response.data.detail[0];
          errorMessage = firstError?.msg || 'Ошибка валидации данных';
        } else if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        }
      }
      
      showNotification(errorMessage, 'danger');
    }
  };
  
  // Обновление промокода
  const handleUpdatePromoCode = async () => {
    try {
      // Проверка, чтобы только одно из полей discount_percent или discount_amount было заполнено
      if (formData.discount_percent && formData.discount_amount) {
        showNotification('Укажите только одно из полей: процент скидки или фиксированную сумму', 'danger');
        return;
      }
      
      // Создаем копию данных формы и преобразуем пустые строки в null для числовых полей
      const dataToSend = {
        ...formData,
        discount_percent: formData.discount_percent === '' ? null : 
                          formData.discount_percent ? parseInt(formData.discount_percent, 10) : null,
        discount_amount: formData.discount_amount === '' ? null : 
                        formData.discount_amount ? parseInt(formData.discount_amount, 10) : null
      };
      
      await axios.put(`${API_URLS.ORDER_SERVICE}/admin/promo-codes/${currentPromoCode.id}`, dataToSend, {
        withCredentials: true
      });
      
      showNotification('Промокод успешно обновлен');
      setShowEditModal(false);
      fetchPromoCodes();
    } catch (err) {
      console.error('Error updating promo code:', err);
      
      // Улучшенная обработка ошибок валидации
      let errorMessage = 'Ошибка обновления промокода';
      
      if (err.response?.data) {
        // Обработка ошибок валидации из Pydantic
        if (err.response.data.detail && Array.isArray(err.response.data.detail)) {
          // Берем первую ошибку из списка ошибок валидации
          const firstError = err.response.data.detail[0];
          errorMessage = firstError?.msg || 'Ошибка валидации данных';
        } else if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        }
      }
      
      showNotification(errorMessage, 'danger');
    }
  };
  
  // Удаление промокода
  const handleDeletePromoCode = async () => {
    try {
      await axios.delete(`${API_URLS.ORDER_SERVICE}/admin/promo-codes/${currentPromoCode.id}`, {
        withCredentials: true
      });
      
      showNotification('Промокод успешно удален');
      setShowDeleteModal(false);
      fetchPromoCodes();
    } catch (err) {
      console.error('Error deleting promo code:', err);
      showNotification(err.response?.data?.detail || 'Ошибка удаления промокода', 'danger');
    }
  };
  
  // Фильтрация промокодов
  const filteredPromoCodes = promoCodes.filter(promoCode => {
    // Фильтр по статусу
    if (filterStatus === 'active' && !promoCode.is_active) return false;
    if (filterStatus === 'inactive' && promoCode.is_active) return false;
    
    // Фильтр по поисковому запросу
    if (searchTerm && !promoCode.code.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    
    return true;
  });
  
  return (
    <Container fluid className="py-4">
      <h1 className="mb-4">Управление промокодами</h1>
      
      {/* Уведомление */}
      {notification.show && (
        <Alert variant={notification.variant} dismissible onClose={() => setNotification({ show: false, message: '', variant: 'success' })}>
          {notification.message}
        </Alert>
      )}
      
      {/* Панель инструментов */}
      <Row className="mb-4">
        <Col md={6} className="mb-2 mb-md-0">
          <InputGroup>
            <FormControl
              placeholder="Поиск по коду промокода"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <Button variant="outline-secondary" onClick={() => setSearchTerm('')}>
              Очистить
            </Button>
          </InputGroup>
        </Col>
        <Col md={3} className="mb-2 mb-md-0">
          <Form.Select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">Все статусы</option>
            <option value="active">Активные</option>
            <option value="inactive">Неактивные</option>
          </Form.Select>
        </Col>
        <Col md={3} className="text-end">
          <Button variant="primary" onClick={handleShowCreateModal}>
            <i className="bi bi-plus-lg me-1"></i> Создать промокод
          </Button>
        </Col>
      </Row>
      
      {/* Загрузка и ошибки */}
      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" role="status" variant="primary">
            <span className="visually-hidden">Загрузка...</span>
          </Spinner>
          <p className="mt-2">Загрузка промокодов...</p>
        </div>
      ) : error ? (
        <Alert variant="danger">{error}</Alert>
      ) : filteredPromoCodes.length === 0 ? (
        <Alert variant="info">
          {searchTerm || filterStatus !== 'all' 
            ? 'Нет промокодов, соответствующих критериям поиска.' 
            : 'В системе нет промокодов. Нажмите \"Создать промокод\" для добавления.'}
        </Alert>
      ) : (
        /* Таблица промокодов */
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>ID</th>
              <th>Код</th>
              <th>Скидка</th>
              <th>Активен до</th>
              <th>Статус</th>
              <th>Дата создания</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {filteredPromoCodes.map(promoCode => (
              <tr key={promoCode.id}>
                <td>{promoCode.id}</td>
                <td>{promoCode.code}</td>
                <td>
                  {promoCode.discount_percent 
                    ? `${promoCode.discount_percent}%` 
                    : `${promoCode.discount_amount} ₽`}
                </td>
                <td>{formatDateTime(promoCode.valid_until)}</td>
                <td>
                  <Badge bg={promoCode.is_active ? 'success' : 'danger'}>
                    {promoCode.is_active ? 'Активен' : 'Неактивен'}
                  </Badge>
                </td>
                <td>{formatDateTime(promoCode.created_at)}</td>
                <td>
                  <Button 
                    variant="outline-primary" 
                    size="sm" 
                    className="me-1"
                    onClick={() => handleShowEditModal(promoCode)}
                  >
                    <i className="bi bi-pencil"></i>
                  </Button>
                  <Button 
                    variant="outline-danger" 
                    size="sm"
                    onClick={() => handleShowDeleteModal(promoCode)}
                  >
                    <i className="bi bi-trash"></i>
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      
      {/* Модальное окно создания промокода */}
      <Modal show={showCreateModal} onHide={() => setShowCreateModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Создание промокода</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Код промокода*</Form.Label>
              <Form.Control
                type="text"
                name="code"
                value={formData.code}
                onChange={handleInputChange}
                required
              />
              <Form.Text className="text-muted">
                Уникальный код промокода, который будут использовать пользователи
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Процент скидки</Form.Label>
              <Form.Control
                type="number"
                name="discount_percent"
                value={formData.discount_percent}
                onChange={handleInputChange}
                min="1"
                max="100"
              />
              <Form.Text className="text-muted">
                Укажите процент скидки (от 1 до 100%)
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Фиксированная сумма скидки</Form.Label>
              <Form.Control
                type="number"
                name="discount_amount"
                value={formData.discount_amount}
                onChange={handleInputChange}
                min="1"
              />
              <Form.Text className="text-muted">
                Укажите фиксированную сумму скидки в рублях
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Действителен до*</Form.Label>
              <Form.Control
                type="datetime-local"
                name="valid_until"
                value={formData.valid_until}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                name="is_active"
                label="Активен"
                checked={formData.is_active}
                onChange={handleInputChange}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
            Отмена
          </Button>
          <Button variant="primary" onClick={handleCreatePromoCode}>
            Создать
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Модальное окно редактирования промокода */}
      <Modal show={showEditModal} onHide={() => setShowEditModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Редактирование промокода</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Код промокода*</Form.Label>
              <Form.Control
                type="text"
                name="code"
                value={formData.code}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Процент скидки</Form.Label>
              <Form.Control
                type="number"
                name="discount_percent"
                value={formData.discount_percent}
                onChange={handleInputChange}
                min="1"
                max="100"
              />
              <Form.Text className="text-muted">
                Заполните это поле ИЛИ поле &quot;Фиксированная сумма скидки&quot;, но не оба
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Фиксированная сумма скидки</Form.Label>
              <Form.Control
                type="number"
                name="discount_amount"
                value={formData.discount_amount}
                onChange={handleInputChange}
                min="1"
              />
              <Form.Text className="text-muted">
                Заполните это поле ИЛИ поле &quot;Процент скидки&quot;, но не оба
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Действителен до*</Form.Label>
              <Form.Control
                type="datetime-local"
                name="valid_until"
                value={formData.valid_until}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                name="is_active"
                label="Активен"
                checked={formData.is_active}
                onChange={handleInputChange}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowEditModal(false)}>
            Отмена
          </Button>
          <Button variant="primary" onClick={handleUpdatePromoCode}>
            Сохранить
          </Button>
        </Modal.Footer>
      </Modal>
      
      {/* Модальное окно удаления промокода */}
      <Modal show={showDeleteModal} onHide={() => setShowDeleteModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Удаление промокода</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Вы уверены, что хотите удалить промокод <strong>{currentPromoCode?.code}</strong>?</p>
          <p className="text-danger">Это действие нельзя отменить.</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
            Отмена
          </Button>
          <Button variant="danger" onClick={handleDeletePromoCode}>
            Удалить
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default AdminPromoCodes; 