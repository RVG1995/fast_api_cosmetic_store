import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { adminAPI } from '../../utils/api';

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [permissions, setPermissions] = useState({
    canMakeAdmin: false,
    canDeleteUser: false
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
        
        setPermissions({
          canMakeAdmin,
          canDeleteUser
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
  }, []);

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

  const handleActivate = async (userId) => {
    try {
      await adminAPI.activateUser(userId);
      
      // Обновляем пользователя в списке
      setUsers(users.map(user => 
        user.id === userId ? { ...user, is_active: true } : user
      ));
    } catch (err) {
      setError('Ошибка при активации пользователя');
      console.error(err);
    }
  };

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
    if (!window.confirm('Вы уверены, что хотите отозвать права администратора у этого пользователя?')) {
      return;
    }
    
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
    if (!window.confirm('Вы уверены, что хотите удалить этого пользователя?')) {
      return;
    }
    
    try {
      await adminAPI.deleteUser(userId);
      
      // Удаляем пользователя из списка
      setUsers(users.filter(user => user.id !== userId));
    } catch (err) {
      setError('Ошибка при удалении пользователя');
      console.error(err);
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
                        {!user.is_active && (
                          <button 
                            className="btn btn-outline-success"
                            onClick={() => handleActivate(user.id)}
                          >
                            Активировать
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
    </div>
  );
};

export default AdminUsers;
