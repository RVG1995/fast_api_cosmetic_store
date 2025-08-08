import React, { useState, useEffect } from "react";
import { Modal, Button, Form, Spinner, Alert, Row, Col, Table } from "react-bootstrap";
import { deliveryAPI, adminAPI, productAPI } from "../../utils/api";
import { formatPrice } from "../../utils/helpers";
import BoxberryPickupModal from '../cart/BoxberryPickupModal';

const forbiddenStatuses = ["Оплачен", "Отправлен", "Доставлен", "Отменен"];

const EditOrderModal = ({ order, show, onHide, onOrderUpdated, statuses }) => {
  const [editOrder, setEditOrder] = useState(null);
  const [deliveryCost, setDeliveryCost] = useState(null);
  const [loading, setLoading] = useState(false);
  const [calcLoading, setCalcLoading] = useState(false);
  const [error, setError] = useState(null);
  const [allProducts, setAllProducts] = useState([]);
  const [productSearch, setProductSearch] = useState("");
  const [productSearchResults, setProductSearchResults] = useState([]);
  const [statusList, setStatusList] = useState(statuses || []);
  const [showBoxberryModal, setShowBoxberryModal] = useState(false);
  const [addressOptions, setAddressOptions] = useState([]);
  const [selectedAddressData, setSelectedAddressData] = useState(null);
  const [addressInput, setAddressInput] = useState("");
  const [addressLoading, setAddressLoading] = useState(false);

  useEffect(() => {
    if (show && order) {
      setEditOrder({
        ...order,
        items: order.items.map(i => ({ ...i })),
        delivery_info: { ...order.delivery_info }
      });
      setDeliveryCost(order.delivery_info?.delivery_cost || order.delivery_cost || 0);
      setError(null);
      setAddressInput(order.delivery_address || "");
      setSelectedAddressData(null);
      setAddressOptions([]);
    }
  }, [show, order]);

  useEffect(() => {
    if (!show) return;
    productAPI.getAdminProducts(1, 100)
      .then(res => setAllProducts(res.data.items || []))
      .catch(() => setAllProducts([]));
  }, [show]);

  useEffect(() => {
    if (statuses && statuses.length) return;
    adminAPI.getOrderById(order.id)
      .then(() => adminAPI.getOrderStatsByDate())
      .then(res => setStatusList(res.statuses || []))
      .catch(() => {});
  }, [order, statuses]);

  // DaData подсказки
  useEffect(() => {
    if (!show || !editOrder) return;
    if (editOrder.delivery_info?.delivery_type !== 'boxberry_courier') return;
    if (!addressInput || addressInput.length < 3) {
      setAddressOptions([]);
      return;
    }
    setAddressLoading(true);
    deliveryAPI.getDadataAddressSuggestions(addressInput)
      .then(data => setAddressOptions(data.suggestions || []))
      .catch(() => setAddressOptions([]))
      .finally(() => setAddressLoading(false));
  }, [addressInput, editOrder?.delivery_info?.delivery_type, show]);

  // Автоматически подставлять выбранный адрес из DaData
  const handleSelectAddress = (suggestion) => {
    setAddressInput(suggestion.value);
    setSelectedAddressData(suggestion.data);
    setAddressOptions([]);
    setEditOrder(prev => ({ ...prev, delivery_address: suggestion.value }));
  };

  // Пересчёт стоимости доставки
  useEffect(() => {
    if (!editOrder) return;
    const items = editOrder.items.map(item => ({
      product_id: item.product_id,
      quantity: item.quantity,
      weight: item.product_weight || 500,
      width: item.product_width || 10,
      height: item.product_height || 10,
      depth: item.product_depth || 10,
      price: item.product_price,
    }));
    const data = {
      items,
      delivery_type: editOrder.delivery_info?.delivery_type || editOrder.delivery_type,
      is_payment_on_delivery: editOrder.is_payment_on_delivery,
    };
    if (editOrder.delivery_info?.boxberry_point_id)
      data.pvz_code = String(editOrder.delivery_info.boxberry_point_id);
    if (editOrder.delivery_info?.delivery_type === "boxberry_courier") {
      let zip = null;
      if (selectedAddressData && selectedAddressData.postal_code) {
        zip = selectedAddressData.postal_code;
      } else if (editOrder.delivery_address) {
        zip = (editOrder.delivery_address.match(/\b\d{6}\b/) || [])[0];
      }
      if (zip) data.zip_code = zip;
    }
    setCalcLoading(true);
    deliveryAPI.calculateDeliveryFromCart(data)
      .then(res => setDeliveryCost(res.price))
      .catch(() => setDeliveryCost(0))
      .finally(() => setCalcLoading(false));
  }, [
    editOrder?.items,
    editOrder?.delivery_info?.delivery_type,
    editOrder?.delivery_info?.boxberry_point_id,
    editOrder?.delivery_address,
    editOrder?.is_payment_on_delivery,
    selectedAddressData
  ]);

  // --- Обработчики ---
  // Клиент
  const handleClientField = (field, value) => {
    setEditOrder(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Доставка
  const handleDeliveryTypeChange = (e) => {
    const val = e.target.value;
    setEditOrder(prev => ({
      ...prev,
      delivery_info: {
        ...prev.delivery_info,
        delivery_type: val,
        boxberry_point_id: null,
        boxberry_point_address: null,
      }
    }));
    setAddressInput("");
    setSelectedAddressData(null);
    setAddressOptions([]);
  };
  const handleDeliveryAddressChange = (e) => {
    setAddressInput(e.target.value);
    setEditOrder(prev => ({
      ...prev,
      delivery_address: e.target.value
    }));
  };
  // Boxberry ПВЗ
  const handlePickupPointSelected = (point) => {
    setEditOrder(prev => ({
      ...prev,
      delivery_info: {
        ...prev.delivery_info,
        boxberry_point_id: point.Code,
        boxberry_point_address: point.Address
      },
      delivery_address: point.Address
    }));
    setShowBoxberryModal(false);
  };

  // Оплата
  const handlePaymentChange = (e) => {
    setEditOrder(prev => ({
      ...prev,
      is_payment_on_delivery: e.target.value === "true"
    }));
  };

  // Статус
  const handleStatusChange = (e) => {
    setEditOrder(prev => ({
      ...prev,
      status: { ...prev.status, id: e.target.value, name: statusList.find(s => s.id == e.target.value)?.name }
    }));
  };

  // Товары
  const handleItemQtyChange = (itemId, qty) => {
    if (qty < 1) return;
    setEditOrder(prev => ({
      ...prev,
      items: prev.items.map(i => i.id === itemId ? { ...i, quantity: qty } : i)
    }));
  };
  const handleRemoveItem = (itemId) => {
    setEditOrder(prev => ({
      ...prev,
      items: prev.items.filter(i => i.id !== itemId)
    }));
  };
  const handleProductSearch = (e) => {
    const val = e.target.value;
    setProductSearch(val);
    if (!val) {
      setProductSearchResults([]);
      return;
    }
    setProductSearchResults(
      allProducts.filter(
        p =>
          p.name.toLowerCase().includes(val.toLowerCase()) ||
          (p.sku && p.sku.toLowerCase().includes(val.toLowerCase())) ||
          p.id.toString().includes(val)
      )
    );
  };
  const handleAddProduct = (product) => {
    if (editOrder.items.some(i => i.product_id === product.id)) return;
    setEditOrder(prev => ({
      ...prev,
      items: [
        ...prev.items,
        {
          id: Math.random(),
          product_id: product.id,
          product_name: product.name,
          product_price: product.price,
          quantity: 1,
          total_price: product.price,
        }
      ]
    }));
    setProductSearch("");
    setProductSearchResults([]);
  };

  // Сохранение
  const handleSave = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Сначала отправляем изменения товаров, если есть
      await adminAPI.updateOrderItems(order.id, {
        items_to_add: editOrder.items.filter(i => !order.items.some(oi => oi.product_id === i.product_id)).map(i => ({ product_id: i.product_id, quantity: i.quantity })),
        items_to_update: Object.fromEntries(
          editOrder.items
            .filter(i => order.items.some(oi => oi.product_id === i.product_id && oi.quantity !== i.quantity))
            .map(i => [order.items.find(oi => oi.product_id === i.product_id).id, i.quantity])
        ),
        items_to_remove: order.items.filter(oi => !editOrder.items.some(i => i.product_id === oi.product_id)).map(i => i.id)
      });
      // 2. Затем отправляем основные поля заказа (без товаров)
      const updateData = {
        delivery_info: {
          delivery_type: editOrder.delivery_info?.delivery_type,
          boxberry_point_id: editOrder.delivery_info?.boxberry_point_id,
          boxberry_point_address: editOrder.delivery_info?.boxberry_point_address,
          delivery_cost: deliveryCost,
        },
        delivery_address: editOrder.delivery_address,
        status_id: editOrder.status?.id,
        is_payment_on_delivery: editOrder.is_payment_on_delivery,
        full_name: editOrder.full_name,
        email: editOrder.email,
        phone: editOrder.phone,
        comment: editOrder.comment,
      };
      await adminAPI.updateOrder(order.id, updateData);
      // 3. После любых изменений делаем GET заказа и обновляем стейт
      const freshOrder = await adminAPI.getOrderById(order.id);
      onOrderUpdated(freshOrder);
      onHide();
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Ошибка сохранения заказа');
    } finally {
      setLoading(false);
    }
  };

  if (!editOrder) return null;
  const isBlocked = forbiddenStatuses.includes(order.status?.name);

  // Суммы
  const totalProducts = editOrder.items.reduce((sum, i) => sum + (i.product_price * i.quantity), 0);
  const total = totalProducts + (deliveryCost || 0);

  return (
    <Modal show={show} onHide={onHide} size="xl" centered>
      <Modal.Header closeButton>
        <Modal.Title>Редактировать заказ #{order.id}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {isBlocked && (
          <Alert variant="warning">
            Редактирование заказа недоступно для статуса &quot;{order.status?.name}&quot;
          </Alert>
        )}
        {error && <Alert variant="danger">{error}</Alert>}

        {/* 1. Данные клиента */}
        <h5>Данные клиента</h5>
        <Row>
          <Col md={4}>
            <Form.Group>
              <Form.Label>ФИО</Form.Label>
              <Form.Control
                type="text"
                value={editOrder.full_name || ""}
                onChange={e => handleClientField("full_name", e.target.value)}
                disabled={isBlocked}
              />
            </Form.Group>
          </Col>
          <Col md={4}>
            <Form.Group>
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                value={editOrder.email || ""}
                onChange={e => handleClientField("email", e.target.value)}
                disabled={isBlocked}
              />
            </Form.Group>
          </Col>
          <Col md={4}>
            <Form.Group>
              <Form.Label>Телефон</Form.Label>
              <Form.Control
                type="text"
                value={editOrder.phone || ""}
                onChange={e => handleClientField("phone", e.target.value)}
                disabled={isBlocked}
              />
            </Form.Group>
          </Col>
        </Row>
        <Form.Group className="mt-2">
          <Form.Label>Комментарий</Form.Label>
          <Form.Control
            as="textarea"
            rows={2}
            value={editOrder.comment || ""}
            onChange={e => handleClientField("comment", e.target.value)}
            disabled={isBlocked}
          />
        </Form.Group>

        {/* 2. Доставка */}
        <h5 className="mt-4">Доставка</h5>
        <Row>
          <Col md={4}>
            <Form.Group>
              <Form.Label>Тип доставки</Form.Label>
              <Form.Select
                value={editOrder.delivery_info?.delivery_type || ""}
                onChange={handleDeliveryTypeChange}
                disabled={isBlocked}
              >
                <option value="">Выберите тип доставки</option>
                <option value="boxberry_pickup_point">Пункт выдачи BoxBerry</option>
                <option value="boxberry_courier">Курьер BoxBerry</option>
              </Form.Select>
            </Form.Group>
          </Col>
          <Col md={8}>
            {editOrder.delivery_info?.delivery_type === "boxberry_pickup_point" ? (
              <div className="d-flex align-items-end gap-2">
                <Form.Group className="flex-grow-1">
                  <Form.Label>Пункт выдачи</Form.Label>
                  <Form.Control
                    type="text"
                    value={editOrder.delivery_info?.boxberry_point_address || ""}
                    readOnly
                    disabled={isBlocked}
                  />
                </Form.Group>
                <Button
                  variant="outline-primary"
                  onClick={() => setShowBoxberryModal(true)}
                  disabled={isBlocked}
                >
                  {editOrder.delivery_info?.boxberry_point_id ? "Изменить ПВЗ" : "Выбрать ПВЗ"}
                </Button>
              </div>
            ) : editOrder.delivery_info?.delivery_type === "boxberry_courier" ? (
              <div className="position-relative">
                <Form.Group>
                  <Form.Label>Адрес доставки</Form.Label>
                  <Form.Control
                    type="text"
                    value={addressInput}
                    onChange={handleDeliveryAddressChange}
                    disabled={isBlocked}
                    autoComplete="off"
                  />
                  {addressLoading && <Spinner size="sm" className="ms-2" />}
                  {addressOptions.length > 0 && (
                    <div className="position-absolute w-100 border bg-white shadow-sm" style={{ zIndex: 1000, maxHeight: 300, overflowY: 'auto' }}>
                      {addressOptions.map((s, idx) => (
                        <button
                          key={idx}
                          type="button"
                          className="w-100 text-start p-2 border-0 bg-white border-bottom search-result-item"
                          onClick={() => handleSelectAddress(s)}
                        >
                          {s.value}
                        </button>
                      ))}
                    </div>
                  )}
                </Form.Group>
              </div>
            ) : null}
          </Col>
        </Row>
        <BoxberryPickupModal
          show={showBoxberryModal}
          onHide={() => setShowBoxberryModal(false)}
          onPickupPointSelected={handlePickupPointSelected}
          selectedAddress={editOrder.delivery_address}
        />

        {/* 3. Оплата */}
        <h5 className="mt-4">Оплата</h5>
        <Form.Group>
          <Form.Check
            type="radio"
            label="Оплата при получении"
            name="payment"
            value="true"
            checked={!!editOrder.is_payment_on_delivery}
            onChange={handlePaymentChange}
            disabled={isBlocked}
          />
          <Form.Check
            type="radio"
            label="Оплата на сайте"
            name="payment"
            value="false"
            checked={!editOrder.is_payment_on_delivery}
            onChange={handlePaymentChange}
            disabled={isBlocked}
          />
        </Form.Group>

        {/* 4. Статус заказа */}
        <h5 className="mt-4">Статус заказа</h5>
        <Form.Group>
          <Form.Label>Статус</Form.Label>
          <Form.Select
            value={editOrder.status?.id || ""}
            onChange={handleStatusChange}
            disabled={isBlocked}
          >
            <option value="">Выберите статус</option>
            {statusList.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </Form.Select>
        </Form.Group>

        {/* 5. Товары */}
        <h5 className="mt-4">Товары</h5>
        <Row className="mb-2">
          <Col md={6}>
            <Form.Control
              type="text"
              placeholder="Поиск товара по названию, SKU или ID"
              value={productSearch}
              onChange={handleProductSearch}
              disabled={isBlocked}
            />
            {productSearchResults.length > 0 && (
              <div className="border bg-white position-absolute w-100" style={{ zIndex: 1000 }}>
                {productSearchResults.map(p => (
                  <button
                    key={p.id}
                    type="button"
                    className="w-100 text-start p-2 border-0 bg-white border-bottom"
                    onClick={() => handleAddProduct(p)}
                  >
                    {p.name} (ID: {p.id}, {formatPrice(p.price)}, остаток: {p.stock})
                  </button>
                ))}
              </div>
            )}
          </Col>
        </Row>
        <Table responsive hover>
          <thead>
            <tr>
              <th>ID</th>
              <th>Наименование</th>
              <th>Цена</th>
              <th>Кол-во</th>
              <th>Сумма</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {editOrder.items.map(item => (
              <tr key={item.id}>
                <td>{item.product_id}</td>
                <td>{item.product_name}</td>
                <td>{formatPrice(item.product_price)}</td>
                <td>
                  <Form.Control
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={e => handleItemQtyChange(item.id, parseInt(e.target.value) || 1)}
                    disabled={isBlocked}
                    style={{ width: 80 }}
                  />
                </td>
                <td>{formatPrice(item.product_price * item.quantity)}</td>
                <td>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleRemoveItem(item.id)}
                    disabled={isBlocked}
                  >
                    Удалить
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>

        {/* 6. Суммы */}
        <div className="mt-4">
          <Row>
            <Col md={4} className="mb-2">
              <strong>Стоимость товаров:</strong> {formatPrice(totalProducts)}
            </Col>
            <Col md={4} className="mb-2">
              <strong>Стоимость доставки:</strong> {calcLoading ? <Spinner size="sm" /> : formatPrice(deliveryCost)}
            </Col>
            <Col md={4} className="mb-2">
              <strong>Итого:</strong> {formatPrice(total)}
            </Col>
          </Row>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>Отмена</Button>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={loading || isBlocked}
        >
          {loading ? <Spinner size="sm" /> : "Сохранить"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default EditOrderModal; 