import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Table, 
  Form, 
  Row, 
  Col, 
  Modal, 
  Alert, 
  Badge,
  Spinner
} from 'react-bootstrap';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';
import { useAuth } from '../../context/AuthContext';

const ORDER_SERVICE_URL = API_URLS.ORDER_SERVICE;

const AdminOrderStatuses = () => {
  const { user } = useAuth();
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Состояние для модального окна создания/редактирования
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
  const [selectedStatus, setSelectedStatus] = useState(null);
  
  // Состояние формы
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    color: '#3498db',
    allow_cancel: true,
    is_final: false,
    sort_order: 0
  });
  
  // Состояние для модального окна удаления
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [statusToDelete, setStatusToDelete] = useState(null);
  
  // Загрузка статусов при монтировании компонента
  useEffect(() => {
    loadStatuses();
  }, []);
  
  // Функция для загрузки статусов заказов
  const loadStatuses = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      const response = await axios.get(`${ORDER_SERVICE_URL}/order-statuses`, config);
      
      // Сортируем статусы по порядку сортировки
      const sortedStatuses = response.data.sort((a, b) => a.sort_order - b.sort_order);
      setStatuses(sortedStatuses);
    } catch (err) {
      console.error('Ошибка при загрузке статусов заказов:', err);
      setError('Не удалось загрузить статусы заказов. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };
  
  // Открытие модального окна для создания нового статуса
  const handleCreateStatus = () => {
    setFormData({
      name: '',
      description: '',
      color: '#3498db',
      allow_cancel: true,
      is_final: false,
      sort_order: statuses.length > 0 ? Math.max(...statuses.map(s => s.sort_order)) + 1 : 1
    });
    setModalMode('create');
    setShowModal(true);
  };
  
  // Открытие модального окна для редактирования статуса
  const handleEditStatus = (status) => {
    setSelectedStatus(status);
    setFormData({
      name: status.name,
      description: status.description || '',
      color: status.color,
      allow_cancel: status.allow_cancel,
      is_final: status.is_final,
      sort_order: status.sort_order
    });
    setModalMode('edit');
    setShowModal(true);
  };
  
  // Открытие модального окна для удаления статуса
  const handleDeleteStatus = (status) => {
    setStatusToDelete(status);
    setShowDeleteModal(true);
  };
  
  // Закрытие модальных окон
  const handleCloseModal = () => {
    setShowModal(false);
    setShowDeleteModal(false);
    setSelectedStatus(null);
    setStatusToDelete(null);
  };
  
  // Обработка изменения полей формы
  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };
  
  // Сохранение статуса (создание или редактирование)
  const handleSaveStatus = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const config = {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      let response;
      
      if (modalMode === 'create') {
        // Создание нового статуса
        response = await axios.post(
          `${ORDER_SERVICE_URL}/order-statuses`, 
          formData, 
          config
        );
        setSuccess('Статус заказа успешно создан');
      } else {
        // Редактирование существующего статуса
        response = await axios.put(
          `${ORDER_SERVICE_URL}/order-statuses/${selectedStatus.id}`, 
          formData, 
          config
        );
        setSuccess('Статус заказа успешно обновлен');
      }
      
      // Обновляем список статусов
      await loadStatuses();
      
      // Закрываем модальное окно
      setShowModal(false);
      
      // Автоматически скрываем сообщение об успехе через 3 секунды
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Ошибка при сохранении статуса заказа:', err);
      
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Не удалось сохранить статус заказа. Пожалуйста, попробуйте позже.');
      }
    } finally {
      setLoading(false);
    }
  };
  
  // Удаление статуса
  const handleConfirmDelete = async () => {
    if (!statusToDelete) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const config = {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      await axios.delete(
        `${ORDER_SERVICE_URL}/order-statuses/${statusToDelete.id}`, 
        config
      );
      
      // Обновляем список статусов
      await loadStatuses();
      
      // Закрываем модальное окно
      setShowDeleteModal(false);
      
      // Показываем сообщение об успехе
      setSuccess('Статус заказа успешно удален');
      
      // Автоматически скрываем сообщение об успехе через 3 секунды
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Ошибка при удалении статуса заказа:', err);
      
      if (err.response?.status === 400 && err.response?.data?.detail) {
        // Скорее всего, статус используется в заказах
        setError(err.response.data.detail);
      } else {
        setError('Не удалось удалить статус заказа. Пожалуйста, попробуйте позже.');
      }
      
      setShowDeleteModal(false);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Управление статусами заказов</h2>
        <Button 
          variant="primary" 
          onClick={handleCreateStatus}
          disabled={loading}
        >
          Создать новый статус
        </Button>
      </div>
      
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert variant="success" className="mb-4">
          {success}
        </Alert>
      )}
      
      <Card>
        <Card.Body>
          {loading && !statuses.length ? (
            <div className="text-center py-5">
              <Spinner animation="border" role="status">
                <span className="visually-hidden">Загрузка...</span>
              </Spinner>
            </div>
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>Порядок</th>
                  <th>Название</th>
                  <th>Описание</th>
                  <th>Цвет</th>
                  <th>Отмена разрешена</th>
                  <th>Финальный статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {statuses.map(status => (
                  <tr key={status.id}>
                    <td>{status.sort_order}</td>
                    <td>
                      <Badge 
                        style={{ 
                          backgroundColor: status.color,
                          color: isDarkColor(status.color) ? 'white' : 'black'
                        }}
                      >
                        {status.name}
                      </Badge>
                    </td>
                    <td>{status.description || '-'}</td>
                    <td>
                      <div 
                        className="color-preview" 
                        style={{ 
                          backgroundColor: status.color,
                          width: '20px',
                          height: '20px',
                          borderRadius: '4px',
                          display: 'inline-block'
                        }}
                      />
                      <span className="ms-2">{status.color}</span>
                    </td>
                    <td>{status.allow_cancel ? 'Да' : 'Нет'}</td>
                    <td>{status.is_final ? 'Да' : 'Нет'}</td>
                    <td>
                      <Button 
                        variant="outline-primary" 
                        size="sm"
                        className="me-2"
                        onClick={() => handleEditStatus(status)}
                      >
                        Редактировать
                      </Button>
                      <Button 
                        variant="outline-danger" 
                        size="sm"
                        onClick={() => handleDeleteStatus(status)}
                      >
                        Удалить
                      </Button>
                    </td>
                  </tr>
                ))}
                
                {statuses.length === 0 && (
                  <tr>
                    <td colSpan="7" className="text-center py-3">
                      Статусы заказов не найдены
                    </td>
                  </tr>
                )}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
      
      {/* Модальное окно создания/редактирования статуса */}
      <Modal show={showModal} onHide={handleCloseModal} backdrop="static">
        <Modal.Header closeButton>
          <Modal.Title>
            {modalMode === 'create' ? 'Создание статуса заказа' : 'Редактирование статуса заказа'}
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveStatus}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Название статуса</Form.Label>
              <Form.Control
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                placeholder="Введите название статуса"
                minLength={2}
                maxLength={50}
              />
              <Form.Text className="text-muted">
                Название статуса должно быть от 2 до 50 символов
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Описание</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                placeholder="Введите описание статуса (необязательно)"
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Цвет</Form.Label>
              <div className="d-flex align-items-center">
                <Form.Control
                  type="color"
                  name="color"
                  value={formData.color}
                  onChange={handleInputChange}
                  required
                  title="Выберите цвет для статуса"
                />
                <Form.Control
                  type="text"
                  name="color"
                  value={formData.color}
                  onChange={handleInputChange}
                  required
                  className="ms-2"
                  pattern="^#[0-9A-Fa-f]{6}$"
                  placeholder="#RRGGBB"
                />
              </div>
              <Form.Text className="text-muted">
                Используйте HEX-формат, например: #3498db
              </Form.Text>
            </Form.Group>
            
            <Row className="mb-3">
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Check 
                    type="checkbox"
                    id="allow-cancel"
                    name="allow_cancel"
                    label="Разрешить отмену заказа"
                    checked={formData.allow_cancel}
                    onChange={handleInputChange}
                  />
                  <Form.Text className="text-muted">
                    Если отмечено, то заказ в этом статусе можно отменить
                  </Form.Text>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Check 
                    type="checkbox"
                    id="is-final"
                    name="is_final"
                    label="Финальный статус"
                    checked={formData.is_final}
                    onChange={handleInputChange}
                  />
                  <Form.Text className="text-muted">
                    Финальный статус означает, что заказ выполнен или отменен
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>
            
            <Form.Group className="mb-3">
              <Form.Label>Порядок сортировки</Form.Label>
              <Form.Control
                type="number"
                name="sort_order"
                value={formData.sort_order}
                onChange={handleInputChange}
                required
                min={1}
              />
              <Form.Text className="text-muted">
                Определяет порядок отображения статусов в списках
              </Form.Text>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={handleCloseModal}>
              Отмена
            </Button>
            <Button 
              variant="primary" 
              type="submit"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Spinner
                    as="span"
                    animation="border"
                    size="sm"
                    role="status"
                    aria-hidden="true"
                  />
                  <span className="ms-2">Сохранение...</span>
                </>
              ) : (
                'Сохранить'
              )}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
      
      {/* Модальное окно подтверждения удаления */}
      <Modal show={showDeleteModal} onHide={handleCloseModal}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение удаления</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {statusToDelete && (
            <p>
              Вы уверены, что хотите удалить статус "{statusToDelete.name}"?
              <br/>
              <strong>Это действие нельзя будет отменить.</strong>
            </p>
          )}
          <Alert variant="warning">
            <strong>Внимание!</strong> Удаление статуса возможно только если он не используется ни в одном заказе.
          </Alert>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseModal}>
            Отмена
          </Button>
          <Button 
            variant="danger" 
            onClick={handleConfirmDelete}
            disabled={loading}
          >
            {loading ? (
              <>
                <Spinner
                  as="span"
                  animation="border"
                  size="sm"
                  role="status"
                  aria-hidden="true"
                />
                <span className="ms-2">Удаление...</span>
              </>
            ) : (
              'Удалить'
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

// Вспомогательная функция для определения светлый/темный цвет
const isDarkColor = (hexColor) => {
  // Конвертируем HEX в RGB
  const r = parseInt(hexColor.substring(1, 3), 16);
  const g = parseInt(hexColor.substring(3, 5), 16);
  const b = parseInt(hexColor.substring(5, 7), 16);
  
  // Вычисляем яркость по формуле
  // Если яркость < 128, то цвет темный, иначе светлый
  return (r * 0.299 + g * 0.587 + b * 0.114) < 128;
};

export default AdminOrderStatuses; 