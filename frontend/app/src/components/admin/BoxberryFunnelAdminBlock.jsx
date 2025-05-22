import React, { useEffect, useState } from "react";
import axios from "axios";
import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';

const API_BASE = process.env.REACT_APP_ORDER_API_URL || "http://localhost:8003";

export default function BoxberryFunnelAdminBlock() {
  const [rules, setRules] = useState([]);
  const [orderStatuses, setOrderStatuses] = useState([]);
  const [boxberryStatuses, setBoxberryStatuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editRule, setEditRule] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    setLoading(true);
    try {
      const [rulesRes, statusesRes, boxberryRes] = await Promise.all([
        axios.get(`${API_BASE}/boxberry-funnel`, { withCredentials: true }),
        axios.get(`${API_BASE}/order-statuses`, { withCredentials: true }),
        axios.get(`${API_BASE}/boxberry-funnel/boxberry-statuses`, { withCredentials: true }),
      ]);
      setRules(rulesRes.data);
      setOrderStatuses(statusesRes.data);
      setBoxberryStatuses(boxberryRes.data);
    } catch (e) {
      // Можно добавить обработку ошибок
      setRules([]);
      setOrderStatuses([]);
      setBoxberryStatuses([]);
    } finally {
      setLoading(false);
    }
  }

  function handleAdd() {
    setEditRule({
      id: 0,
      boxberry_status_code: boxberryStatuses[0]?.code || 1,
      boxberry_status_name: boxberryStatuses[0]?.name || "",
      order_status_id: orderStatuses[0]?.id || 1,
      active: true,
    });
    setShowModal(true);
  }

  function handleEdit(rule) {
    setEditRule({ ...rule });
    setShowModal(true);
  }

  async function handleDelete(id) {
    if (!window.confirm("Удалить правило?")) return;
    await axios.delete(`${API_BASE}/boxberry-funnel/${id}`, { withCredentials: true });
    fetchAll();
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!editRule) return;
    const payload = {
      boxberry_status_code: editRule.boxberry_status_code,
      boxberry_status_name: editRule.boxberry_status_name,
      order_status_id: editRule.order_status_id,
      active: editRule.active,
    };
    try {
      if (editRule.id) {
        await axios.put(`${API_BASE}/boxberry-funnel/${editRule.id}`, payload, { withCredentials: true });
      } else {
        await axios.post(`${API_BASE}/boxberry-funnel`, payload, { withCredentials: true });
      }
      setShowModal(false);
      setEditRule(null);
      fetchAll();
    } catch (err) {
      if (err.response && err.response.status === 409) {
        alert('Такое правило уже существует');
      } else if (err.response && err.response.status === 400 && err.response.data?.detail?.includes('unique')) {
        alert('Такое правило уже существует');
      } else if (err.response && err.response.data?.detail?.includes('duplicate')) {
        alert('Такое правило уже существует');
      } else {
        alert('Ошибка при сохранении');
      }
    }
  }

  // Сортируем правила по boxberry_status_code по возрастанию
  const sortedRules = [...rules].sort((a, b) => a.boxberry_status_code - b.boxberry_status_code);

  // Сортируем boxberryStatuses по code по возрастанию
  const sortedBoxberryStatuses = [...boxberryStatuses].sort((a, b) => a.code - b.code);

  return (
    <div className="card my-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Воронка статусов Boxberry → статусы заказа</h5>
        <button className="btn btn-primary btn-sm" onClick={handleAdd}>
          Добавить правило
        </button>
      </div>
      <div className="card-body">
        {loading ? (
          <div>Загрузка...</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-bordered table-sm align-middle">
              <thead>
                <tr>
                  <th>Boxberry код</th>
                  <th>Boxberry статус</th>
                  <th>Статус заказа</th>
                  <th>Активен</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sortedRules.map((r) => (
                  <tr key={r.id}>
                    <td>{r.boxberry_status_code}</td>
                    <td>{r.boxberry_status_name}</td>
                    <td>{r.order_status?.name || r.order_status_id}</td>
                    <td>
                      {r.active ? (
                        <span className="badge bg-success">Да</span>
                      ) : (
                        <span className="badge bg-secondary">Нет</span>
                      )}
                    </td>
                    <td>
                      <button className="btn btn-sm btn-outline-primary me-2" onClick={() => handleEdit(r)}>
                        Редактировать
                      </button>
                      <button className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(r.id)}>
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
                {rules.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center text-muted">
                      Нет правил
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && editRule && (
        <Modal show={showModal} onHide={() => setShowModal(false)} dialogClassName="modal-90w" backdrop="static" keyboard={false}>
          <Modal.Header closeButton>
            <Modal.Title>{editRule ? "Редактировать правило" : "Добавить правило"}</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <form onSubmit={handleSave}>
              <div className="mb-3">
                <label className="form-label">Статус Boxberry</label>
                <div style={{overflowX: 'auto', minWidth: 0}}>
                  <select
                    className="form-select"
                    style={{minWidth: 400, maxWidth: '100%'}}
                    value={editRule.boxberry_status_code}
                    onChange={e => {
                      const code = Number(e.target.value);
                      const found = sortedBoxberryStatuses.find(s => s.code === code);
                      setEditRule(er => er ? { ...er, boxberry_status_code: code, boxberry_status_name: found?.name || "" } : er);
                    }}
                  >
                    {sortedBoxberryStatuses.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="mb-3">
                <label className="form-label">Статус заказа</label>
                <div style={{overflowX: 'auto', minWidth: 0}}>
                  <select
                    className="form-select"
                    style={{minWidth: 300, maxWidth: '100%'}}
                    value={editRule.order_status_id}
                    onChange={e => setEditRule(er => er ? { ...er, order_status_id: Number(e.target.value) } : er)}
                  >
                    {orderStatuses.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-check mb-3">
                <input
                  className="form-check-input"
                  type="checkbox"
                  checked={editRule.active}
                  id="activeCheck"
                  onChange={e => setEditRule(er => er ? { ...er, active: e.target.checked } : er)}
                />
                <label className="form-check-label" htmlFor="activeCheck">
                  Активно
                </label>
              </div>
              <div className="d-flex justify-content-end gap-2">
                <Button variant="secondary" onClick={() => setShowModal(false)}>
                  Закрыть
                </Button>
                <Button type="submit" variant="primary">
                  Сохранить
                </Button>
              </div>
            </form>
          </Modal.Body>
        </Modal>
      )}
    </div>
  );
} 