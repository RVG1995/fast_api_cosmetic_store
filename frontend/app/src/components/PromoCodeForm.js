import React, { useState } from 'react';
import { Form, Button, Spinner } from 'react-bootstrap';
import { useOrders } from '../context/OrderContext';

const PromoCodeForm = ({ email, phone, onPromoCodeApplied }) => {
  const [code, setCode] = useState('');
  const { checkPromoCode, loading } = useOrders();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    
    try {
      const result = await checkPromoCode(code, email, phone);
      if (result && result.is_valid) {
        onPromoCodeApplied(result);
      }
    } catch (err) {
      console.error('Ошибка при проверке промокода:', err);
    }
  };
  
  return (
    <Form onSubmit={handleSubmit} className="promo-code-form">
      <Form.Group>
        <Form.Label>Промокод</Form.Label>
        <div className="d-flex">
          <Form.Control
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Введите промокод"
            disabled={loading}
          />
          <Button 
            variant="outline-primary" 
            type="submit"
            disabled={loading || !code.trim()}
            className="ms-2"
          >
            {loading ? (
              <Spinner
                as="span"
                animation="border"
                size="sm"
                role="status"
                aria-hidden="true"
              />
            ) : (
              'Применить'
            )}
          </Button>
        </div>
      </Form.Group>
    </Form>
  );
};

export default PromoCodeForm; 