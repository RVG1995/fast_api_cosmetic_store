import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Form, Button, Row, Col, Spinner, Alert, Table } from 'react-bootstrap';
import { adminAPI } from '../../utils/api';
import { formatPrice } from '../../utils/helpers';
import Chart from 'chart.js/auto';
import '../../styles/AdminDashboard.css';

const AdminReports = () => {
  // Состояние для хранения данных отчета
  const [reportData, setReportData] = useState(null);
  // Состояние для периода отчета
  const [dateRange, setDateRange] = useState({
    date_from: new Date().toISOString().split('T')[0], // Текущий день
    date_to: new Date().toISOString().split('T')[0]
  });
  // Состояние для загрузки данных
  const [loading, setLoading] = useState(false);
  // Состояние для ошибок
  const [error, setError] = useState(null);
  
  // Ссылки на элементы Canvas для графиков
  const orderStatusChartRef = useRef(null);
  const ordersChartRef = useRef(null);
  
  // Состояние для выбранного предустановленного периода
  const [selectedPeriod, setSelectedPeriod] = useState('today');
  
  // Состояние для загрузки отчета
  const [downloadLoading, setDownloadLoading] = useState({
    csv: false,
    excel: false,
    pdf: false,
    word: false
  });
  
  // Функция для обновления даты начала и конца периода
  const updateDateRange = (newRange) => {
    setDateRange(newRange);
  };
  
  // Функция для изменения периода вручную
  const handleDateChange = (e) => {
    const { name, value } = e.target;
    setDateRange(prev => ({
      ...prev,
      [name]: value
    }));
    // Сбрасываем выбранный период, так как даты изменились вручную
    setSelectedPeriod('custom');
  };
  
  // Функция для установки предустановленного периода
  const setPredefinedPeriod = useCallback((period) => {
    setSelectedPeriod(period);
    
    const today = new Date();
    let from = new Date();
    let to = new Date();
    
    switch (period) {
      case 'today':
        // Текущий день (с начала дня до конца дня)
        from = today;
        to = today;
        break;
      case 'week':
        // Текущая неделя (с понедельника до воскресенья)
        const dayOfWeek = today.getDay() || 7; // Если 0 (воскресенье), то 7
        from = new Date(today);
        from.setDate(today.getDate() - dayOfWeek + 1); // Понедельник
        to = new Date(from);
        to.setDate(from.getDate() + 6); // Воскресенье
        break;
      case 'month':
        // Текущий месяц (с 1-го числа до последнего)
        from = new Date(today.getFullYear(), today.getMonth(), 1);
        to = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        break;
      case 'year':
        // Текущий год (с 1 января до 31 декабря)
        from = new Date(today.getFullYear(), 0, 1);
        to = new Date(today.getFullYear(), 11, 31);
        break;
      default:
        // По умолчанию - текущий день
        from = today;
        to = today;
    }
    
    updateDateRange({
      date_from: from.toISOString().split('T')[0],
      date_to: to.toISOString().split('T')[0]
    });
  }, []);
  
  // Функция для генерации отчета
  const generateReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await adminAPI.getOrderStatsByDate(dateRange.date_from, dateRange.date_to);
      setReportData(data);
    } catch (err) {
      console.error('Ошибка при получении данных отчета:', err);
      setError('Не удалось получить данные для отчета. Пожалуйста, попробуйте позже.');
    } finally {
      setLoading(false);
    }
  }, [dateRange.date_from, dateRange.date_to]);
  
  // Функция для скачивания отчета
  const handleGenerateReport = async (format) => {
    try {
      setDownloadLoading({ ...downloadLoading, [format]: true });
      
      // Получаем отчет в выбранном формате
      await adminAPI.generateOrderReport(
        format, 
        dateRange.date_from, 
        dateRange.date_to
      );
      
      setError(null);
    } catch (err) {
      console.error(`Ошибка при скачивании отчета в формате ${format}:`, err);
      setError(`Не удалось скачать отчет в формате ${format}. Пожалуйста, попробуйте позже.`);
    } finally {
      setDownloadLoading({ ...downloadLoading, [format]: false });
    }
  };
  
  // Эффект для рендеринга графиков после загрузки данных
  useEffect(() => {
    // Если данные есть и рефы на canvas существуют, рендерим графики
    if (reportData && orderStatusChartRef.current && ordersChartRef.current) {
      // Уничтожаем существующие графики, если они были
      Chart.getChart(orderStatusChartRef.current)?.destroy();
      Chart.getChart(ordersChartRef.current)?.destroy();
      
      // График распределения заказов по статусам
      const statusLabels = Object.keys(reportData.orders_by_status);
      const statusData = Object.values(reportData.orders_by_status);
      
      // Генерируем цвета для графика статусов
      const statusColors = statusLabels.map((_, index) => {
        // Простая палитра цветов
        const colors = [
          'rgba(75, 192, 192, 0.7)',
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 206, 86, 0.7)',
          'rgba(255, 99, 132, 0.7)',
          'rgba(153, 102, 255, 0.7)',
          'rgba(255, 159, 64, 0.7)',
          'rgba(199, 199, 199, 0.7)'
        ];
        return colors[index % colors.length];
      });
      
      // Создаем график статусов
      new Chart(orderStatusChartRef.current, {
        type: 'pie',
        data: {
          labels: statusLabels,
          datasets: [{
            data: statusData,
            backgroundColor: statusColors,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          plugins: {
            title: {
              display: true,
              text: 'Распределение заказов по статусам'
            },
            legend: {
              position: 'right'
            }
          }
        }
      });
      
      // График суммы и количества заказов
      new Chart(ordersChartRef.current, {
        type: 'bar',
        data: {
          labels: ['Показатели заказов'],
          datasets: [
            {
              label: 'Всего заказов',
              data: [reportData.total_orders],
              backgroundColor: 'rgba(54, 162, 235, 0.7)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 1
            },
            {
              label: 'Общая сумма (в тыс. руб.)',
              data: [Math.round(reportData.total_revenue / 1000)],
              backgroundColor: 'rgba(255, 99, 132, 0.7)',
              borderColor: 'rgba(255, 99, 132, 1)',
              borderWidth: 1
            },
            {
              label: 'Сумма отмененных (в тыс. руб.)',
              data: [Math.round(reportData.canceled_orders_revenue / 1000)],
              backgroundColor: 'rgba(255, 159, 64, 0.7)',
              borderColor: 'rgba(255, 159, 64, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true
            }
          },
          plugins: {
            title: {
              display: true,
              text: 'Показатели заказов'
            },
            legend: {
              position: 'top'
            }
          }
        }
      });
    }
  }, [reportData]);
  
  // При первой загрузке компонента устанавливаем текущий день и загружаем данные
  const didInitRef = useRef(false);
  useEffect(() => {
    if (didInitRef.current) return;
    didInitRef.current = true;
    setPredefinedPeriod('today');
    generateReport();
  }, [setPredefinedPeriod, generateReport]);
  
  return (
    <div className="admin-reports">
      <h1 className="mb-4">Формирование отчета</h1>
      
      {/* Карточка с выбором периода */}
      <Card className="mb-4">
        <Card.Header>
          <h3>Выберите период отчета</h3>
        </Card.Header>
        <Card.Body>
          {/* Кнопки быстрого выбора периода */}
          <div className="mb-4">
            <Row>
              <Col xs={12}>
                <div className="period-buttons d-flex gap-2 flex-wrap">
                  <Button 
                    variant={selectedPeriod === 'today' ? 'primary' : 'outline-primary'} 
                    onClick={() => setPredefinedPeriod('today')}
                  >
                    Сегодня
                  </Button>
                  <Button 
                    variant={selectedPeriod === 'week' ? 'primary' : 'outline-primary'} 
                    onClick={() => setPredefinedPeriod('week')}
                  >
                    Текущая неделя
                  </Button>
                  <Button 
                    variant={selectedPeriod === 'month' ? 'primary' : 'outline-primary'} 
                    onClick={() => setPredefinedPeriod('month')}
                  >
                    Текущий месяц
                  </Button>
                  <Button 
                    variant={selectedPeriod === 'year' ? 'primary' : 'outline-primary'} 
                    onClick={() => setPredefinedPeriod('year')}
                  >
                    Текущий год
                  </Button>
                </div>
              </Col>
            </Row>
          </div>
          
          {/* Форма ручного выбора периода */}
          <Form>
            <Row>
              <Col md={5}>
                <Form.Group className="mb-3">
                  <Form.Label>Дата начала</Form.Label>
                  <Form.Control
                    type="date"
                    name="date_from"
                    value={dateRange.date_from}
                    onChange={handleDateChange}
                  />
                </Form.Group>
              </Col>
              
              <Col md={5}>
                <Form.Group className="mb-3">
                  <Form.Label>Дата окончания</Form.Label>
                  <Form.Control
                    type="date"
                    name="date_to"
                    value={dateRange.date_to}
                    onChange={handleDateChange}
                  />
                </Form.Group>
              </Col>
              
              <Col md={2} className="d-flex align-items-end">
                <Button 
                  variant="success" 
                  className="w-100 mb-3" 
                  onClick={generateReport}
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
                        className="me-2"
                      />
                      Загрузка...
                    </>
                  ) : (
                    <>Сформировать</>
                  )}
                </Button>
              </Col>
            </Row>
          </Form>
        </Card.Body>
      </Card>
      
      {/* Отображение ошибки, если она есть */}
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}
      
      {/* Отображение отчета */}
      {reportData && !loading && (
        <>
          <Card className="mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h3>Отчет по заказам</h3>
              <div className="download-buttons">
                <Button 
                  variant="outline-primary" 
                  className="me-2" 
                  onClick={() => handleGenerateReport('csv')}
                  disabled={downloadLoading.csv}
                >
                  {downloadLoading.csv ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                      <span className="ms-2">Загрузка CSV...</span>
                    </>
                  ) : 'Скачать CSV'}
                </Button>
                
                <Button 
                  variant="outline-success" 
                  onClick={() => handleGenerateReport('excel')}
                  disabled={downloadLoading.excel}
                >
                  {downloadLoading.excel ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                      <span className="ms-2">Загрузка Excel...</span>
                    </>
                  ) : 'Скачать Excel'}
                </Button>
                
                <Button 
                  variant="outline-danger" 
                  onClick={() => handleGenerateReport('pdf')}
                  disabled={downloadLoading.pdf}
                >
                  {downloadLoading.pdf ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                      <span className="ms-2">Загрузка PDF...</span>
                    </>
                  ) : 'Скачать PDF'}
                </Button>
                
                <Button 
                  variant="outline-info" 
                  onClick={() => handleGenerateReport('word')}
                  disabled={downloadLoading.word}
                >
                  {downloadLoading.word ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                      <span className="ms-2">Загрузка Word...</span>
                    </>
                  ) : 'Скачать Word'}
                </Button>
              </div>
            </Card.Header>
            <Card.Body>
              <Row className="mb-4">
                <Col md={6}>
                  <h4 className="mb-3">Общая статистика</h4>
                  <Table striped bordered hover>
                    <tbody>
                      <tr>
                        <td><strong>Всего заказов</strong></td>
                        <td>{reportData.total_orders}</td>
                      </tr>
                      <tr>
                        <td><strong>Общая сумма заказов</strong></td>
                        <td>{formatPrice(reportData.total_revenue)}</td>
                      </tr>
                      <tr>
                        <td><strong>Средняя стоимость заказа</strong></td>
                        <td>{formatPrice(reportData.average_order_value)}</td>
                      </tr>
                      <tr>
                        <td><strong>Сумма отмененных заказов</strong></td>
                        <td>{formatPrice(reportData.canceled_orders_revenue)}</td>
                      </tr>
                    </tbody>
                  </Table>
                  
                  <h4 className="mb-3 mt-4">Заказы по статусам</h4>
                  <Table striped bordered hover>
                    <thead>
                      <tr>
                        <th>Статус</th>
                        <th>Количество</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(reportData.orders_by_status).map(([status, count]) => (
                        <tr key={status}>
                          <td>{status}</td>
                          <td>{count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </Col>
                <Col md={6}>
                  <div className="charts">
                    <div className="chart-container mb-4">
                      <canvas ref={orderStatusChartRef}></canvas>
                    </div>
                    <div className="chart-container">
                      <canvas ref={ordersChartRef}></canvas>
                    </div>
                  </div>
                </Col>
              </Row>
              
              <div className="text-center text-muted mb-3">
                <p>
                  Период отчета: {dateRange.date_from} - {dateRange.date_to}
                </p>
              </div>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default AdminReports; 