import React, { useState, useEffect } from 'react';
import { Modal, Button, Spinner, Form, ListGroup, Alert } from 'react-bootstrap';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';
import './BoxberryPickupModal.css';

const BoxberryPickupModal = ({ show, onHide, onPickupPointSelected, selectedAddress }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cityName, setCityName] = useState('');
  const [cityCode, setCityCode] = useState(null);
  const [pickupPoints, setPickupPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCityInput, setShowCityInput] = useState(false);
  const [cityInputValue, setCityInputValue] = useState('');
  const [citySearchResults, setCitySearchResults] = useState([]);
  const [searchingCity, setSearchingCity] = useState(false);

  // Извлекаем название города из адреса или показываем поле ввода города
  useEffect(() => {
    if (!selectedAddress || selectedAddress.trim() === '') {
      setShowCityInput(true);
      setCityName('');
      return;
    }
    
    setShowCityInput(false);
    
    // Ищем название города в строке адреса
    const addressParts = selectedAddress.split(',').map(part => part.trim());
    // Обычно город идет в начале адреса или после региона
    let cityCandidate = '';
    
    // Ищем часть адреса, которая может быть городом
    for (const part of addressParts) {
      if (part.toLowerCase().startsWith('г ') || part.toLowerCase().startsWith('г. ')) {
        cityCandidate = part.replace(/^г\.?\s+/i, '');
        break;
      }
    }
    
    // Если не нашли по "г.", берем вторую часть адреса как город
    if (!cityCandidate && addressParts.length > 1) {
      cityCandidate = addressParts[1];
    }
    
    setCityName(cityCandidate);
    console.log("Извлеченный город:", cityCandidate);
  }, [selectedAddress]);

  // Функция поиска города
  const searchCity = async (query) => {
    if (!query || query.trim().length < 3) {
      setCitySearchResults([]);
      return;
    }
    
    try {
      setSearchingCity(true);
      const response = await axios.get(`${API_URLS.DELIVERY_SERVICE}/delivery/boxberry/cities`);
      
      if (response.data && Array.isArray(response.data)) {
        const cities = response.data;
        const filteredCities = cities.filter(city => 
          city.Name.toLowerCase().includes(query.toLowerCase()) || 
          (city.UniqName && city.UniqName.toLowerCase().includes(query.toLowerCase()))
        );
        
        setCitySearchResults(filteredCities.slice(0, 10)); // Ограничиваем результаты первыми 10
      }
    } catch (err) {
      console.error("Ошибка при поиске города:", err);
    } finally {
      setSearchingCity(false);
    }
  };

  // Обработчик выбора города из результатов поиска
  const handleCitySelect = (city) => {
    setCityName(city.Name);
    setCityInputValue(city.Name);
    setCityCode(city.Code);
    setCitySearchResults([]);
  };

  // Обработчик изменения поля ввода города
  const handleCityInputChange = (e) => {
    const value = e.target.value;
    setCityInputValue(value);
    searchCity(value);
  };

  // Обработчик кнопки поиска города
  const handleSearchCity = () => {
    if (cityInputValue.trim()) {
      setCityName(cityInputValue);
    }
  };

  // Загружаем код города, когда изменяется название города
  useEffect(() => {
    const fetchCityCode = async () => {
      if (!cityName || cityCode) return; // Если уже есть код города, не запрашиваем
      
      try {
        setLoading(true);
        setError(null);
        
        const response = await axios.get(`${API_URLS.DELIVERY_SERVICE}/delivery/boxberry/find-city-code`, {
          params: { city_name: cityName }
        });
        
        if (response.data.city_code) {
          setCityCode(response.data.city_code);
          console.log(`Найден код города для ${cityName}: ${response.data.city_code}`);
        } else {
          setError(`Город ${cityName} не найден в системе BoxBerry`);
          console.log(`Город ${cityName} не найден`);
        }
      } catch (err) {
        setError(`Ошибка при поиске города: ${err.message}`);
        console.error('Ошибка при поиске кода города:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchCityCode();
  }, [cityName, cityCode]);

  // Сбрасываем состояние при открытии модального окна
  useEffect(() => {
    if (show) {
      setSelectedPoint(null);
      setSearchQuery('');
      
      // Если адрес пустой, сбрасываем cityCode и показываем поле ввода города
      if (!selectedAddress || selectedAddress.trim() === '') {
        setCityCode(null);
        setCityInputValue('');
      }
    }
  }, [show, selectedAddress]);

  // Загружаем пункты выдачи, когда получаем код города
  useEffect(() => {
    const fetchPickupPoints = async () => {
      if (!cityCode) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const response = await axios.get(`${API_URLS.DELIVERY_SERVICE}/delivery/boxberry/pickup-points`, {
          params: { city_code: cityCode }
        });
        
        if (response.data.simplified_data && response.data.simplified_data.length > 0) {
          setPickupPoints(response.data.simplified_data);
          console.log(`Загружено ${response.data.simplified_data.length} пунктов выдачи`);
        } else {
          setError(`Пункты выдачи в городе ${cityName} не найдены`);
          console.log('Пункты выдачи не найдены');
        }
      } catch (err) {
        setError(`Ошибка при загрузке пунктов выдачи: ${err.message}`);
        console.error('Ошибка при загрузке пунктов выдачи:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchPickupPoints();
  }, [cityCode, cityName]);

  // Обработчик выбора пункта выдачи
  const handleSelectPoint = (point) => {
    setSelectedPoint(point);
  };

  // Обработчик подтверждения выбора
  const handleConfirm = () => {
    if (selectedPoint) {
      onPickupPointSelected(selectedPoint);
      onHide();
    }
  };

  // Фильтрация пунктов выдачи по поисковому запросу
  const filteredPoints = pickupPoints.filter(point => {
    const searchLower = searchQuery.toLowerCase();
    return (
      point.Name.toLowerCase().includes(searchLower) ||
      point.Address.toLowerCase().includes(searchLower)
    );
  });

  return (
    <Modal 
      show={show} 
      onHide={onHide}
      size="lg"
      centered
      backdrop="static"
      className="boxberry-modal"
    >
      <Modal.Header closeButton>
        <Modal.Title>Выбор пункта выдачи BoxBerry</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {/* Блок для ручного ввода города, если адрес пустой или не удалось найти город */}
        {(showCityInput || error) && (
          <div className="city-input-block mb-4">
            <Form.Group className="mb-3">
              <Form.Label>Введите город для поиска пунктов выдачи</Form.Label>
              <div className="d-flex">
                <Form.Control
                  type="text"
                  value={cityInputValue}
                  onChange={handleCityInputChange}
                  placeholder="Например: Москва"
                  className="me-2"
                />
                <Button 
                  variant="primary" 
                  onClick={handleSearchCity}
                  disabled={!cityInputValue.trim() || searchingCity}
                >
                  {searchingCity ? <Spinner size="sm" animation="border" /> : "Найти"}
                </Button>
              </div>
              {citySearchResults.length > 0 && (
                <div className="city-suggestions position-relative mt-1">
                  <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                    {citySearchResults.map((city, i) => (
                      <div
                        key={i}
                        className="suggestion-item px-2 py-1 hover-bg-light"
                        onClick={() => handleCitySelect(city)}
                      >
                        {city.UniqName || city.Name}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Form.Group>
          </div>
        )}
        
        {loading && (
          <div className="text-center py-4">
            <Spinner animation="border" variant="primary" />
            <p className="mt-2">Загрузка пунктов выдачи...</p>
          </div>
        )}
        
        {error && !showCityInput && (
          <Alert variant="danger">
            {error}
            <div className="mt-2">
              <Form.Group className="mb-3">
                <Form.Label>Изменить город</Form.Label>
                <Form.Control
                  type="text"
                  value={cityName}
                  onChange={(e) => setCityName(e.target.value)}
                  placeholder="Введите название города"
                />
              </Form.Group>
            </div>
          </Alert>
        )}
        
        {!loading && !error && pickupPoints.length > 0 && (
          <>
            <div className="current-city mb-3">
              <strong>Город: </strong> {cityName}
            </div>
            
            <Form.Group className="mb-3">
              <Form.Label>Поиск пункта выдачи</Form.Label>
              <Form.Control
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Введите адрес или название"
              />
            </Form.Group>
            
            <div className="pickup-points-container">
              <ListGroup>
                {filteredPoints.map((point) => (
                  <ListGroup.Item 
                    key={point.Code}
                    action
                    active={selectedPoint && selectedPoint.Code === point.Code}
                    onClick={() => handleSelectPoint(point)}
                    className="pickup-point-item"
                  >
                    <div className="pickup-point-name">{point.Name}</div>
                    <div className="pickup-point-address">{point.Address}</div>
                    <div className="pickup-point-schedule">
                      <small>График работы: {point.WorkShedule}</small>
                    </div>
                    {point.DeliveryPeriod && (
                      <div className="pickup-point-delivery">
                        <small>Срок доставки: {point.DeliveryPeriod}</small>
                      </div>
                    )}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            </div>
          </>
        )}
        
        {!loading && !error && pickupPoints.length === 0 && cityName && (
          <Alert variant="info">
            Введите город и нажмите "Найти" для поиска пунктов выдачи
          </Alert>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Отмена
        </Button>
        <Button 
          variant="primary" 
          onClick={handleConfirm}
          disabled={!selectedPoint || loading}
        >
          Выбрать
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default BoxberryPickupModal; 