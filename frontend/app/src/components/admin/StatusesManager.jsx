import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Card, Button, Table, Form, Row, Col, Modal, Alert, Badge, Spinner } from 'react-bootstrap';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';

const ORDER_SERVICE_URL = API_URLS.ORDER_SERVICE;

const isDarkColor = (hexColor) => {
  const r = parseInt(hexColor.substring(1, 3), 16);
  const g = parseInt(hexColor.substring(3, 5), 16);
  const b = parseInt(hexColor.substring(5, 7), 16);
  return (r * 0.299 + g * 0.587 + b * 0.114) < 128;
};

const StatusesManager = ({
  pageTitle,
  resourcePath, // 'order-statuses' | 'payment-statuses'
  emptyListText,
  createModalTitle,
  editModalTitle,
  createSuccessMsg,
  updateSuccessMsg,
  deleteSuccessMsg,
  loadErrorMsg,
  saveErrorMsg,
  deleteErrorMsg,
  extraFieldDefs = [], // [{ name, label, type: 'checkbox'|'text'|'number', help? }]
  initialExtraFields = {},
  tableExtraColumns = [], // [{ header, render: (row) => node }]
}) => {
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [selectedStatus, setSelectedStatus] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [statusToDelete, setStatusToDelete] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    color: '#3498db',
    sort_order: 0,
    ...initialExtraFields,
  });

  useEffect(() => {
    loadStatuses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadStatuses = async () => {
    setLoading(true);
    setError(null);
    try {
      const config = { withCredentials: true, headers: { 'Content-Type': 'application/json' } };
      const response = await axios.get(`${ORDER_SERVICE_URL}/${resourcePath}`, config);
      const sorted = response.data.sort((a, b) => a.sort_order - b.sort_order);
      setStatuses(sorted);
    } catch (err) {
      setError(loadErrorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setFormData({
      name: '',
      description: '',
      color: '#3498db',
      sort_order: statuses.length > 0 ? Math.max(...statuses.map(s => s.sort_order)) + 1 : 1,
      ...initialExtraFields,
    });
    setModalMode('create');
    setShowModal(true);
  };

  const handleEdit = (status) => {
    setSelectedStatus(status);
    setFormData({
      name: status.name,
      description: status.description || '',
      color: status.color,
      sort_order: status.sort_order,
      ...extraFieldDefs.reduce((acc, f) => ({ ...acc, [f.name]: status[f.name] }), {}),
    });
    setModalMode('edit');
    setShowModal(true);
  };

  const handleDeleteAsk = (status) => {
    setStatusToDelete(status);
    setShowDeleteModal(true);
  };

  const handleCloseModals = () => {
    setShowModal(false);
    setShowDeleteModal(false);
    setSelectedStatus(null);
    setStatusToDelete(null);
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const config = { withCredentials: true, headers: { 'Content-Type': 'application/json' } };
      if (modalMode === 'create') {
        await axios.post(`${ORDER_SERVICE_URL}/${resourcePath}`, formData, config);
        setSuccess(createSuccessMsg);
      } else {
        await axios.put(`${ORDER_SERVICE_URL}/${resourcePath}/${selectedStatus.id}`, formData, config);
        setSuccess(updateSuccessMsg);
      }
      await loadStatuses();
      setShowModal(false);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      if (err.response?.data?.detail) setError(err.response.data.detail);
      else setError(saveErrorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!statusToDelete) return;
    setLoading(true);
    setError(null);
    try {
      const config = { withCredentials: true, headers: { 'Content-Type': 'application/json' } };
      await axios.delete(`${ORDER_SERVICE_URL}/${resourcePath}/${statusToDelete.id}`, config);
      await loadStatuses();
      setShowDeleteModal(false);
      setSuccess(deleteSuccessMsg);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.detail) setError(err.response.data.detail);
      else setError(deleteErrorMsg);
      setShowDeleteModal(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{pageTitle}</h2>
        <Button variant="primary" onClick={handleCreate} disabled={loading}>
          Создать новый статус
        </Button>
      </div>

      {error && <Alert variant="danger" className="mb-4">{error}</Alert>}
      {success && <Alert variant="success" className="mb-4">{success}</Alert>}

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
                  {tableExtraColumns.map((c, idx) => (
                    <th key={idx}>{c.header}</th>
                  ))}
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {statuses.map(status => (
                  <tr key={status.id}>
                    <td>{status.sort_order}</td>
                    <td>
                      <Badge style={{ backgroundColor: status.color, color: isDarkColor(status.color) ? 'white' : 'black' }}>
                        {status.name}
                      </Badge>
                    </td>
                    <td>{status.description || '-'}</td>
                    <td>
                      <div className="color-preview" style={{ backgroundColor: status.color, width: '20px', height: '20px', borderRadius: '4px', display: 'inline-block' }} />
                      <span className="ms-2">{status.color}</span>
                    </td>
                    {tableExtraColumns.map((c, idx) => (
                      <td key={idx}>{c.render(status)}</td>
                    ))}
                    <td>
                      <Button variant="outline-primary" size="sm" className="me-2" onClick={() => handleEdit(status)}>
                        Редактировать
                      </Button>
                      <Button variant="outline-danger" size="sm" onClick={() => handleDeleteAsk(status)}>
                        Удалить
                      </Button>
                    </td>
                  </tr>
                ))}
                {statuses.length === 0 && (
                  <tr>
                    <td colSpan={5 + tableExtraColumns.length} className="text-center py-3">
                      {emptyListText}
                    </td>
                  </tr>
                )}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      <Modal show={showModal} onHide={handleCloseModals} backdrop="static">
        <Modal.Header closeButton>
          <Modal.Title>{modalMode === 'create' ? createModalTitle : editModalTitle}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSave}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Название статуса</Form.Label>
              <Form.Control type="text" name="name" value={formData.name} onChange={handleInputChange} required placeholder="Введите название статуса" minLength={2} maxLength={50} />
              <Form.Text className="text-muted">Название статуса должно быть от 2 до 50 символов</Form.Text>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Описание</Form.Label>
              <Form.Control as="textarea" rows={3} name="description" value={formData.description} onChange={handleInputChange} placeholder="Введите описание статуса (необязательно)" />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Цвет</Form.Label>
              <div className="d-flex align-items-center">
                <Form.Control type="color" name="color" value={formData.color} onChange={handleInputChange} required title="Выберите цвет для статуса" />
                <Form.Control type="text" name="color" value={formData.color} onChange={handleInputChange} required className="ms-2" pattern="^#[0-9A-Fa-f]{6}$" placeholder="#RRGGBB" />
              </div>
              <Form.Text className="text-muted">Используйте HEX-формат, например: #3498db</Form.Text>
            </Form.Group>

            {extraFieldDefs.length > 0 && (
              <Row className="mb-3">
                {extraFieldDefs.map((field) => (
                  <Col md={extraFieldDefs.length > 1 ? 6 : 12} key={field.name}>
                    <Form.Group className="mb-3">
                      {field.type === 'checkbox' ? (
                        <>
                          <Form.Check type="checkbox" id={field.name} name={field.name} label={field.label} checked={!!formData[field.name]} onChange={handleInputChange} />
                          {field.help && <Form.Text className="text-muted">{field.help}</Form.Text>}
                        </>
                      ) : (
                        <>
                          <Form.Label>{field.label}</Form.Label>
                          <Form.Control type={field.type || 'text'} name={field.name} value={formData[field.name] ?? ''} onChange={handleInputChange} />
                          {field.help && <Form.Text className="text-muted">{field.help}</Form.Text>}
                        </>
                      )}
                    </Form.Group>
                  </Col>
                ))}
              </Row>
            )}

            <Form.Group className="mb-3">
              <Form.Label>Порядок сортировки</Form.Label>
              <Form.Control type="number" name="sort_order" value={formData.sort_order} onChange={handleInputChange} required min={1} />
              <Form.Text className="text-muted">Определяет порядок отображения статусов в списках</Form.Text>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={handleCloseModals}>Отмена</Button>
            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? (
                <>
                  <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                  <span className="ms-2">Сохранение...</span>
                </>
              ) : 'Сохранить'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <Modal show={showDeleteModal} onHide={handleCloseModals}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение удаления</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {statusToDelete && (
            <p>
              Вы уверены, что хотите удалить статус &quot;{statusToDelete.name}&quot;?
              <br />
              <strong>Это действие нельзя будет отменить.</strong>
            </p>
          )}
          <Alert variant="warning">
            <strong>Внимание!</strong> Удаление статуса возможно только если он не используется ни в одном заказе.
          </Alert>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseModals}>Отмена</Button>
          <Button variant="danger" onClick={handleConfirmDelete} disabled={loading}>
            {loading ? (
              <>
                <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                <span className="ms-2">Удаление...</span>
              </>
            ) : 'Удалить'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default StatusesManager;

StatusesManager.propTypes = {
  pageTitle: PropTypes.string.isRequired,
  resourcePath: PropTypes.string.isRequired,
  emptyListText: PropTypes.string.isRequired,
  createModalTitle: PropTypes.string.isRequired,
  editModalTitle: PropTypes.string.isRequired,
  createSuccessMsg: PropTypes.string.isRequired,
  updateSuccessMsg: PropTypes.string.isRequired,
  deleteSuccessMsg: PropTypes.string.isRequired,
  loadErrorMsg: PropTypes.string.isRequired,
  saveErrorMsg: PropTypes.string.isRequired,
  deleteErrorMsg: PropTypes.string.isRequired,
  extraFieldDefs: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['checkbox', 'text', 'number']),
      help: PropTypes.string,
    })
  ),
  initialExtraFields: PropTypes.object,
  tableExtraColumns: PropTypes.arrayOf(
    PropTypes.shape({
      header: PropTypes.string.isRequired,
      render: PropTypes.func.isRequired,
    })
  ),
};


