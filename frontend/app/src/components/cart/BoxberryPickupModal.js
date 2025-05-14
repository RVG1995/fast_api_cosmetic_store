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
  const [allCities, setAllCities] = useState([]);
  const [loadingCities, setLoadingCities] = useState(false);

  // Загружаем список всех городов при первом открытии модального окна
  useEffect(() => {
    if (show && allCities.length === 0 && !loadingCities) {
      fetchAllCities();
    }
  }, [show, allCities.length, loadingCities]);

  // Функция загрузки всех городов
  const fetchAllCities = async () => {
    try {
      setLoadingCities(true);
      const response = await axios.get(`${API_URLS.DELIVERY_SERVICE}/delivery/boxberry/cities`);
      
      if (response.data && Array.isArray(response.data)) {
        setAllCities(response.data);
        console.log(`Загружено ${response.data.length} городов из API BoxBerry`);
      }
    } catch (error) {
      console.error('Ошибка при загрузке списка городов:', error);
    } finally {
      setLoadingCities(false);
    }
  };

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
  const searchCity = (query) => {
    if (!query || query.trim().length < 2) {
      setCitySearchResults([]);
      return;
    }
    
    try {
      setSearchingCity(true);
      const queryLower = query.toLowerCase().trim();
      
      if (allCities.length > 0) {
        // Фильтруем города из кэшированного списка
        const filteredCities = allCities.filter(city => {
          const nameMatch = city.Name.toLowerCase().includes(queryLower);
          const uniqNameMatch = city.UniqName && city.UniqName.toLowerCase().includes(queryLower);
          const regionMatch = city.Region && city.Region.toLowerCase().includes(queryLower);
          
          return nameMatch || uniqNameMatch || regionMatch;
        });
        
        // Сначала точные совпадения по имени, затем по региону
        const sortedCities = filteredCities.sort((a, b) => {
          // Приоритет точного совпадения имени
          const aExactName = a.Name.toLowerCase() === queryLower;
          const bExactName = b.Name.toLowerCase() === queryLower;
          
          if (aExactName && !bExactName) return -1;
          if (!aExactName && bExactName) return 1;
          
          // Приоритет начала имени
          const aStartsWithName = a.Name.toLowerCase().startsWith(queryLower);
          const bStartsWithName = b.Name.toLowerCase().startsWith(queryLower);
          
          if (aStartsWithName && !bStartsWithName) return -1;
          if (!aStartsWithName && bStartsWithName) return 1;
          
          // Алфавитный порядок
          return a.Name.localeCompare(b.Name);
        });
        
        setCitySearchResults(sortedCities.slice(0, 15)); // Ограничиваем результаты первыми 15
      } else {
        setCitySearchResults([]);
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
      // Отправляем выбранный пункт выдачи в родительский компонент
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
              <div className="position-relative">
                <div className="d-flex">
                  <Form.Control
                    type="text"
                    value={cityInputValue}
                    onChange={handleCityInputChange}
                    placeholder="Например: Москва"
                    className="me-2"
                    autoComplete="off"
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
                  <div className="city-suggestions-dropdown">
                    <ListGroup className="city-suggestions-list">
                      {citySearchResults.map((city, i) => (
                        <ListGroup.Item
                          key={i}
                          action
                          onClick={() => handleCitySelect(city)}
                          className="city-suggestion-item"
                        >
                          <div className="city-name">{city.Name}</div>
                          {city.Region && (
                            <div className="city-region">{city.Region} {city.District ? `, ${city.District}` : ''}</div>
                          )}
                        </ListGroup.Item>
                      ))}
                    </ListGroup>
                  </div>
                )}
                
                {loadingCities && (
                  <div className="text-center mt-2">
                    <Spinner size="sm" animation="border" variant="secondary" />
                    <span className="ms-2 text-muted">Загрузка списка городов...</span>
                  </div>
                )}
              </div>
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
              {selectedAddress && (
                <Button 
                  variant="outline-secondary" 
                  size="sm" 
                  className="ms-2"
                  onClick={() => {
                    setShowCityInput(true);
                    setCityInputValue(cityName);
                    setSelectedPoint(null);
                    setCityCode(null);
                    setPickupPoints([]);
                  }}
                >
                  Изменить город
                </Button>
              )}
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