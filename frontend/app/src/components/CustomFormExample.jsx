import React from 'react';
import { Button, Card, Row, Col, Spinner } from 'react-bootstrap';
import useForm from '../hooks/useForm';
import FormField from './FormField';

/**
 * Демонстрационный компонент формы, использующий хук useForm и компонент FormField
 */
const CustomFormExample = () => {
  // Начальные значения формы
  const initialValues = {
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    agree: false,
    gender: '',
    age: '',
    comments: ''
  };
  
  // Функция валидации формы
  const validateForm = (values) => {
    const errors = {};
    
    // Валидация имени
    if (!values.name) {
      errors.name = 'Имя обязательно для заполнения';
    } else if (values.name.length < 2) {
      errors.name = 'Имя должно содержать минимум 2 символа';
    }
    
    // Валидация email
    if (!values.email) {
      errors.email = 'Email обязателен для заполнения';
    } else if (!/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(values.email)) {
      errors.email = 'Некорректный email адрес';
    }
    
    // Валидация пароля
    if (!values.password) {
      errors.password = 'Пароль обязателен для заполнения';
    } else if (values.password.length < 6) {
      errors.password = 'Пароль должен содержать минимум 6 символов';
    }
    
    // Валидация подтверждения пароля
    if (values.password !== values.confirmPassword) {
      errors.confirmPassword = 'Пароли не совпадают';
    }
    
    // Валидация телефона
    if (values.phone && !/^\+?\d{10,15}$/.test(values.phone.replace(/\D/g, ''))) {
      errors.phone = 'Пожалуйста, введите корректный номер телефона';
    }
    
    // Валидация согласия с условиями
    if (!values.agree) {
      errors.agree = 'Необходимо согласиться с условиями';
    }
    
    return errors;
  };
  
  // Обработчик отправки формы
  const handleSubmit = async (values) => {
    // Имитация отправки на сервер
    console.log('Отправка формы:', values);
    
    // Имитация задержки сети
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Здесь в реальном приложении был бы API запрос
    return values;
  };
  
  // Инициализация useForm
  const {
    values,
    errors,
    touched,
    isSubmitting,
    isSubmitted,
    isDirty,
    isValid,
    handleChange,
    handleBlur,
    handleSubmit: submitForm,
    resetForm
  } = useForm(initialValues, validateForm, handleSubmit);
  
  // Опции для селекта возраста
  const ageOptions = [
    { value: '', label: 'Выберите возрастную группу' },
    { value: '18-24', label: '18-24' },
    { value: '25-34', label: '25-34' },
    { value: '35-44', label: '35-44' },
    { value: '45+', label: '45 и старше' }
  ];
  
  return (
    <Card className="mb-4">
      <Card.Header>
        <h2 className="h5 mb-0">Пример формы с валидацией</h2>
      </Card.Header>
      <Card.Body>
        {isSubmitted && !isDirty ? (
          <div className="text-center py-4">
            <div className="mb-3 text-success">
              <i className="bi bi-check-circle-fill fs-1"></i>
            </div>
            <h4>Форма успешно отправлена!</h4>
            <p className="text-muted">Спасибо за предоставленную информацию.</p>
            <Button 
              variant="outline-primary" 
              onClick={resetForm}
            >
              Заполнить снова
            </Button>
          </div>
        ) : (
          <form onSubmit={submitForm}>
            <Row>
              <Col md={6}>
                <FormField
                  name="name"
                  label="Имя"
                  placeholder="Введите ваше имя"
                  value={values.name}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  error={errors.name}
                  touched={touched.name}
                  required
                />
              </Col>
              
              <Col md={6}>
                <FormField
                  name="email"
                  label="Email"
                  type="email"
                  placeholder="example@domain.com"
                  value={values.email}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  error={errors.email}
                  touched={touched.email}
                  required
                />
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <FormField
                  name="password"
                  label="Пароль"
                  type="password"
                  placeholder="Введите пароль"
                  value={values.password}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  error={errors.password}
                  touched={touched.password}
                  required
                />
              </Col>
              
              <Col md={6}>
                <FormField
                  name="confirmPassword"
                  label="Подтверждение пароля"
                  type="password"
                  placeholder="Повторите пароль"
                  value={values.confirmPassword}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  error={errors.confirmPassword}
                  touched={touched.confirmPassword}
                  required
                />
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <FormField
                  name="phone"
                  label="Телефон"
                  placeholder="+7 (___) ___-__-__"
                  value={values.phone}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  error={errors.phone}
                  touched={touched.phone}
                  description="Необязательное поле"
                />
              </Col>
              
              <Col md={6}>
                <FormField
                  name="age"
                  label="Возрастная группа"
                  type="select"
                  value={values.age}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  error={errors.age}
                  touched={touched.age}
                  options={ageOptions}
                />
              </Col>
            </Row>
            
            <Row className="mb-3">
              <Col md={6}>
                <div className="mb-3">
                  <label className="form-label d-block">Пол</label>
                  <FormField
                    name="gender"
                    type="radio"
                    label="Мужской"
                    value="male"
                    checked={values.gender === 'male'}
                    onChange={() => handleChange({ target: { name: 'gender', value: 'male' } })}
                    className="me-3"
                  />
                  <FormField
                    name="gender"
                    type="radio"
                    label="Женский"
                    value="female"
                    checked={values.gender === 'female'}
                    onChange={() => handleChange({ target: { name: 'gender', value: 'female' } })}
                  />
                </div>
              </Col>
            </Row>
            
            <FormField
              name="comments"
              label="Комментарии"
              as="textarea"
              placeholder="Введите ваши комментарии здесь..."
              value={values.comments}
              onChange={handleChange}
              onBlur={handleBlur}
              rows={4}
            />
            
            <FormField
              name="agree"
              type="checkbox"
              label="Я согласен с условиями использования"
              checked={values.agree}
              onChange={handleChange}
              onBlur={handleBlur}
              error={errors.agree}
              touched={touched.agree}
              required
            />
            
            <div className="d-flex justify-content-between mt-4">
              <Button 
                variant="outline-secondary" 
                onClick={resetForm}
                disabled={isSubmitting}
              >
                Очистить
              </Button>
              <Button 
                type="submit" 
                variant="primary" 
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Spinner as="span" size="sm" animation="border" className="me-2" />
                    Отправка...
                  </>
                ) : 'Отправить'}
              </Button>
            </div>
          </form>
        )}
      </Card.Body>
      {isDirty && (
        <Card.Footer className="text-muted">
          <small>Форма {isValid ? 'валидна' : 'содержит ошибки'}</small>
        </Card.Footer>
      )}
    </Card>
  );
};

export default CustomFormExample; 