import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, InputGroup, Nav, Tab } from 'react-bootstrap';
import ReviewList from '../../../components/reviews/ReviewList';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../../utils/constants';

const AdminReviewsPage = () => {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [includeHidden, setIncludeHidden] = useState(true);
  const [activeTab, setActiveTab] = useState('store');

  // Обработчик изменения страницы
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  // Обработчик поиска
  const handleSearch = (e) => {
    e.preventDefault();
    // Реализация поиска отзывов - можно добавить в дальнейшем
    console.log("Поиск отзывов:", searchTerm);
  };

  return (
    <Container fluid className="py-4">
      <h1 className="mb-4">Управление отзывами</h1>

      <Row>
        <Col lg={12}>
          <Card className="shadow-sm mb-4">
            <Card.Header className="bg-primary text-white">
              <h5 className="mb-0">Фильтр и поиск отзывов</h5>
            </Card.Header>
            <Card.Body>
              <Row>
                <Col md={6}>
                  <Form onSubmit={handleSearch}>
                    <InputGroup className="mb-3">
                      <Form.Control
                        type="text"
                        placeholder="Поиск по имени пользователя или содержанию отзыва"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                      <Button type="submit" variant="primary">
                        <i className="bi bi-search me-1"></i>
                        Найти
                      </Button>
                    </InputGroup>
                  </Form>
                </Col>
                <Col md={6}>
                  <Form.Check
                    type="switch"
                    id="show-hidden-reviews"
                    label="Показывать скрытые отзывы"
                    checked={includeHidden}
                    onChange={(e) => setIncludeHidden(e.target.checked)}
                  />
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row>
        <Col lg={12}>
          <Card className="shadow-sm mb-4">
            <Card.Header className="bg-primary text-white">
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Список отзывов</h5>
                <Button
                  variant="light"
                  size="sm"
                  onClick={() => navigate(ROUTES.REVIEWS)}
                >
                  <i className="bi bi-eye me-1"></i>
                  Просмотр в обычном режиме
                </Button>
              </div>
            </Card.Header>
            <Card.Body>
              <Tab.Container activeKey={activeTab} onSelect={(key) => setActiveTab(key)}>
                <Nav variant="tabs" className="mb-3">
                  <Nav.Item>
                    <Nav.Link eventKey="store">Отзывы о магазине</Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="products">Отзывы о товарах</Nav.Link>
                  </Nav.Item>
                </Nav>
                <Tab.Content>
                  <Tab.Pane eventKey="store">
                    <ReviewList
                      key={`store-${currentPage}-${includeHidden}`}
                      isAdmin={true}
                      currentPage={currentPage}
                      onPageChange={handlePageChange}
                      includeHidden={includeHidden}
                    />
                  </Tab.Pane>
                  <Tab.Pane eventKey="products">
                    <p className="text-muted mb-3">
                      Здесь отображаются все отзывы о товарах. Для просмотра отзывов на конкретный товар, перейдите на страницу товара.
                    </p>
                    {/* Здесь будет компонент для списка всех отзывов о товарах */}
                    <div className="alert alert-info">
                      Функционал просмотра всех отзывов о товарах в разработке.
                    </div>
                  </Tab.Pane>
                </Tab.Content>
              </Tab.Container>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default AdminReviewsPage; 