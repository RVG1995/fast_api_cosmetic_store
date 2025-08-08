import React, { useState } from 'react';
import { Container, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { authAPI } from '../../utils/api';
import { Link, useNavigate } from 'react-router-dom';

const ChangePasswordPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
    
    // Сбрасываем ошибки при изменении полей
    if (error) setError(null);
  };

  const validateForm = () => {
    // Проверяем, что все поля заполнены
    if (!formData.current_password || !formData.new_password || !formData.confirm_password) {
      setError('Пожалуйста, заполните все поля');
      return false;
    }

    // Проверяем, что новый пароль не совпадает со старым
    if (formData.current_password === formData.new_password) {
      setError('Новый пароль должен отличаться от текущего');
      return false;
    }

    // Проверяем, что новый пароль и подтверждение совпадают
    if (formData.new_password !== formData.confirm_password) {
      setError('Новый пароль и подтверждение не совпадают');
      return false;
    }

    // Проверка минимальной длины пароля
    if (formData.new_password.length < 8) {
      setError('Пароль должен содержать не менее 8 символов');
      return false;
    }

    // Проверка наличия цифры в пароле
    if (!/\d/.test(formData.new_password)) {
      setError('Пароль должен содержать хотя бы одну цифру');
      return false;
    }

    // Проверка наличия буквы в пароле
    if (!/[A-Za-z]/.test(formData.new_password)) {
      setError('Пароль должен содержать хотя бы одну букву');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Валидация формы
    if (!validateForm()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Вызываем API для смены пароля
      await authAPI.changePassword(formData);
      
      // При успешной смене пароля показываем сообщение об успехе
      setSuccess(true);
      
      // Очищаем форму
      setFormData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      
      // Перенаправляем на страницу профиля через 3 секунды
      setTimeout(() => {
        navigate('/user');
      }, 3000);
      
    } catch (err) {
      console.error('Ошибка при смене пароля:', err);
      
      // Обработка различных типов ошибок
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.response?.data?.message) {
        setError(err.response.data.message);
      } else if (err.message) {
        setError(err.message);
      } else {
        setError('Произошла ошибка при смене пароля. Пожалуйста, попробуйте позже.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container className="py-5">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Изменение пароля</h2>
        <Link to="/user" className="btn btn-outline-secondary">
          &larr; Вернуться в профиль
        </Link>
      </div>
      
      <Card className="shadow">
        <Card.Body className="p-4">
          {success ? (
            <Alert variant="success">
              <Alert.Heading>Пароль успешно изменен!</Alert.Heading>
              <p>
                Ваш пароль был успешно обновлен. Вы будете перенаправлены на страницу профиля через несколько секунд.
              </p>
              <hr />
              <div className="d-flex justify-content-end">
                <Button variant="outline-success" onClick={() => navigate('/user')}>
                  Вернуться в профиль
                </Button>
              </div>
            </Alert>
          ) : (
            <Form onSubmit={handleSubmit}>
              {error && (
                <Alert variant="danger" className="mb-4">
                  {error}
                </Alert>
              )}
              
              <Form.Group className="mb-4">
                <Form.Label>Текущий пароль</Form.Label>
                <Form.Control
                  type="password"
                  name="current_password"
                  value={formData.current_password}
                  onChange={handleInputChange}
                  placeholder="Введите ваш текущий пароль"
                  required
                />
              </Form.Group>
              
              <Form.Group className="mb-4">
                <Form.Label>Новый пароль</Form.Label>
                <Form.Control
                  type="password"
                  name="new_password"
                  value={formData.new_password}
                  onChange={handleInputChange}
                  placeholder="Введите новый пароль"
                  required
                />
                <Form.Text className="text-muted">
                  Пароль должен содержать минимум 8 символов, включая хотя бы одну букву и одну цифру.
                </Form.Text>
              </Form.Group>
              
              <Form.Group className="mb-4">
                <Form.Label>Подтверждение нового пароля</Form.Label>
                <Form.Control
                  type="password"
                  name="confirm_password"
                  value={formData.confirm_password}
                  onChange={handleInputChange}
                  placeholder="Повторите новый пароль"
                  required
                />
              </Form.Group>
              
              <div className="d-grid gap-2">
                <Button variant="primary" type="submit" disabled={loading}>
                  {loading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                        className="me-2"
                      />
                      Обновление...
                    </>
                  ) : (
                    'Изменить пароль'
                  )}
                </Button>
              </div>
            </Form>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default ChangePasswordPage; 