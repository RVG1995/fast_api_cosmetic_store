import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { adminAPI } from '../../utils/api';
import { useConfirm } from '../../components/common/ConfirmContext';
import { Modal, Button, Form } from 'react-bootstrap';

const AdminUsers = () => {
  const confirm = useConfirm();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Состояния для модального окна создания пользователя
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createUserForm, setCreateUserForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
    personal_data_agreement: true,
    notification_agreement: true,
    is_admin: false
  });
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [permissions, setPermissions] = useState({
    canMakeAdmin: false,
    canDeleteUser: false,
    canToggleActive: false,
    canCreateUser: false
  });
  const { checkPermission } = useAuth();
  const permissionsChecked = useRef(false);

  useEffect(() => {
    const fetchPermissions = async () => {
      // Предотвращаем повторные запросы
      if (permissionsChecked.current) return;
      
      try {
        const canMakeAdmin = await checkPermission('super_admin_access');
        const canDeleteUser = await checkPermission('super_admin_access');
        const canToggleActive = await checkPermission('super_admin_access');
        const canCreateUser = await checkPermission('super_admin_access');
        
        setPermissions({
          canMakeAdmin,
          canDeleteUser,
          canToggleActive,
          canCreateUser
        });
        
        // Отмечаем, что разрешения проверены
        permissionsChecked.current = true;
      } catch (err) {
        console.error('Ошибка при проверке разрешений:', err);
        // Даже в случае ошибки отмечаем, что проверка выполнена
        permissionsChecked.current = true;
      }
    };

    fetchPermissions();
  }, [checkPermission]);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await adminAPI.getAllUsers();
        setUsers(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Ошибка при загрузке пользователей');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleMakeAdmin = async (userId) => {
    try {
      await adminAPI.makeAdmin(userId);
      
      // Обновляем пользователя в списке
      setUsers(users.map(user => 
        user.id === userId ? { ...user, is_admin: true } : user
      ));
    } catch (err) {
      setError('Ошибка при назначении администратора');
      console.error(err);
    }
  };

  const handleRemoveAdmin = async (userId) => {
    const ok = await confirm({
      title: 'Отозвать права администратора?',
      body: 'Вы действительно хотите отозвать права администратора у этого пользователя?'
    });
    if (!ok) return;

    try {
      await adminAPI.removeAdmin(userId);
      
      // Обновляем пользователя в списке
      setUsers(users.map(user => 
        user.id === userId ? { ...user, is_admin: false } : user
      ));
    } catch (err) {
      setError('Ошибка при отзыве прав администратора');
      console.error(err);
    }
  };

  const handleDelete = async (userId) => {
    const ok = await confirm({
      title: 'Удалить пользователя?',
      body: 'Вы действительно хотите удалить этого пользователя?'
    });
    if (!ok) return;

    try {
      await adminAPI.deleteUser(userId);
      
      // Удаляем пользователя из списка
      setUsers(users.filter(user => user.id !== userId));
    } catch (err) {
      setError('Ошибка при удалении пользователя');
      console.error(err);
    }
  };

  const handleToggleActive = async (userId, currentStatus) => {
    const actionText = currentStatus ? 'деактивировать' : 'активировать';
    const ok = await confirm({
      title: `${currentStatus ? 'Деактивировать' : 'Активировать'} пользователя?`,
      body: `Вы действительно хотите ${actionText} этого пользователя?`
    });
    if (!ok) return;

    try {
      await adminAPI.toggleUserActive(userId);
      
      // Обновляем статус пользователя в списке
      setUsers(users.map(user => 
        user.id === userId ? { ...user, is_active: !user.is_active } : user
      ));
    } catch (err) {
      setError(`Ошибка при изменении статуса пользователя`);
      console.error(err);
    }
  };
  
  // Обработчики для модального окна создания пользователя
  const handleCreateModalOpen = () => setShowCreateModal(true);
  const handleCreateModalClose = () => {
    setShowCreateModal(false);
    setCreateUserForm({
      first_name: '',
      last_name: '',
      email: '',
      password: '',
      confirm_password: '',
      personal_data_agreement: true,
      notification_agreement: true,
      is_admin: false
    });
    setFormErrors({});
  };
  
  const handleCreateUserChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    setCreateUserForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    // Сбрасываем ошибки при изменении поля
    if (formErrors[name]) {
      setFormErrors(prev => ({ ...prev, [name]: null }));
    }
  };
  
  const validateForm = () => {
    const errors = {};
    
    if (!createUserForm.first_name.trim()) {
      errors.first_name = 'Имя обязательно';
    }
    
    if (!createUserForm.last_name.trim()) {
      errors.last_name = 'Фамилия обязательна';
    }
    
    if (!createUserForm.email.trim()) {
      errors.email = 'Email обязателен';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(createUserForm.email)) {
      errors.email = 'Некорректный email';
    }
    
    if (!createUserForm.password) {
      errors.password = 'Пароль обязателен';
    } else if (createUserForm.password.length < 8) {
      errors.password = 'Пароль должен содержать минимум 8 символов';
    }
    
    if (createUserForm.password !== createUserForm.confirm_password) {
      errors.confirm_password = 'Пароли не совпадают';
    }
    
    if (!createUserForm.personal_data_agreement) {
      errors.personal_data_agreement = 'Необходимо согласие на обработку персональных данных';
    }
    
    return errors;
  };
  
  const handleCreateUserSubmit = async (e) => {
    e.preventDefault();
    
    // Валидация формы
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const response = await adminAPI.createUser(createUserForm);
      
      // Добавляем созданного пользователя в список
      const newUser = response.data;
      setUsers(prev => [...prev, {
        ...newUser,
        is_active: true,
        is_admin: createUserForm.is_admin,
        is_super_admin: false
      }]);
      
      // Закрываем модальное окно
      handleCreateModalClose();
      
    } catch (err) {
      console.error('Ошибка при создании пользователя:', err);
      
      if (err.response?.data?.detail) {
        // Обрабатываем ошибку с сервера
        if (err.response.data.detail.includes('Email уже зарегистрирован')) {
          setFormErrors({ email: 'Email уже зарегистрирован' });
        } else {
          setError(`Ошибка: ${err.response.data.detail}`);
        }
      } else {
        setError('Ошибка при создании пользователя');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="text-center py-5"><div className="spinner-border"></div></div>;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  return (
    <div className="container py-5">
      <h2 className="mb-4">Управление пользователями</h2>
      
      {error && <div className="alert alert-danger">{error}</div>}
      
      {permissions.canCreateUser && (
        <button 
          className="btn btn-primary mb-4"
          onClick={handleCreateModalOpen}
        >
          Создать пользователя
        </button>
      )}
      
      <div className="card shadow-sm">
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-striped table-hover">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя</th>
                  <th>Email</th>
                  <th>Статус</th>
                  <th>Роль</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.first_name} {user.last_name}</td>
                    <td>{user.email}</td>
                    <td>
                      {user.is_active ? 
                        <span className="badge bg-success">Активен</span> : 
                        <span className="badge bg-warning">Не активирован</span>
                      }
                    </td>
                    <td>
                      {user.is_super_admin ? 
                        <span className="badge bg-danger">Суперадмин</span> : 
                        user.is_admin ? 
                          <span className="badge bg-primary">Админ</span> : 
                          <span className="badge bg-secondary">Пользователь</span>
                      }
                    </td>
                    <td>
                      <div className="btn-group btn-group-sm">
                        {permissions.canToggleActive && !user.is_super_admin && (
                          <button 
                            className={`btn ${user.is_active ? 'btn-outline-warning' : 'btn-outline-success'}`}
                            onClick={() => handleToggleActive(user.id, user.is_active)}
                          >
                            {user.is_active ? 'Деактивировать' : 'Активировать'}
                          </button>
                        )}
                        
                        {permissions.canMakeAdmin && !user.is_admin && !user.is_super_admin && (
                          <button 
                            className="btn btn-outline-primary"
                            onClick={() => handleMakeAdmin(user.id)}
                          >
                            Сделать админом
                          </button>
                        )}
                        
                        {permissions.canMakeAdmin && user.is_admin && !user.is_super_admin && (
                          <button 
                            className="btn btn-outline-warning"
                            onClick={() => handleRemoveAdmin(user.id)}
                          >
                            Убрать права админа
                          </button>
                        )}
                        
                        {permissions.canDeleteUser && !user.is_super_admin && (
                          <button 
                            className="btn btn-outline-danger"
                            onClick={() => handleDelete(user.id)}
                          >
                            Удалить
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      {/* Модальное окно для создания пользователя */}
      <Modal show={showCreateModal} onHide={handleCreateModalClose}>
        <Modal.Header closeButton>
          <Modal.Title>Создание пользователя</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form onSubmit={handleCreateUserSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Имя</Form.Label>
              <Form.Control
                type="text"
                name="first_name"
                value={createUserForm.first_name}
                onChange={handleCreateUserChange}
                isInvalid={!!formErrors.first_name}
              />
              <Form.Control.Feedback type="invalid">
                {formErrors.first_name}
              </Form.Control.Feedback>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Фамилия</Form.Label>
              <Form.Control
                type="text"
                name="last_name"
                value={createUserForm.last_name}
                onChange={handleCreateUserChange}
                isInvalid={!!formErrors.last_name}
              />
              <Form.Control.Feedback type="invalid">
                {formErrors.last_name}
              </Form.Control.Feedback>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                name="email"
                value={createUserForm.email}
                onChange={handleCreateUserChange}
                isInvalid={!!formErrors.email}
              />
              <Form.Control.Feedback type="invalid">
                {formErrors.email}
              </Form.Control.Feedback>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Пароль</Form.Label>
              <Form.Control
                type="password"
                name="password"
                value={createUserForm.password}
                onChange={handleCreateUserChange}
                isInvalid={!!formErrors.password}
              />
              <Form.Control.Feedback type="invalid">
                {formErrors.password}
              </Form.Control.Feedback>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Подтверждение пароля</Form.Label>
              <Form.Control
                type="password"
                name="confirm_password"
                value={createUserForm.confirm_password}
                onChange={handleCreateUserChange}
                isInvalid={!!formErrors.confirm_password}
              />
              <Form.Control.Feedback type="invalid">
                {formErrors.confirm_password}
              </Form.Control.Feedback>
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                name="personal_data_agreement"
                label="Согласие на обработку персональных данных"
                checked={createUserForm.personal_data_agreement}
                onChange={handleCreateUserChange}
                isInvalid={!!formErrors.personal_data_agreement}
                feedback={formErrors.personal_data_agreement}
                feedbackType="invalid"
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                name="notification_agreement"
                label="Согласие на получение уведомлений"
                checked={createUserForm.notification_agreement}
                onChange={handleCreateUserChange}
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                name="is_admin"
                label="Сделать пользователя администратором"
                checked={createUserForm.is_admin}
                onChange={handleCreateUserChange}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCreateModalClose}>
            Отмена
          </Button>
          <Button 
            variant="primary" 
            onClick={handleCreateUserSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Создание...' : 'Создать пользователя'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default AdminUsers;
