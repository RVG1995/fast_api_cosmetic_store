import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';
import React from 'react';

const LoginModal = ({ onClose }) => {
  return (
    <Modal show={true} onHide={onClose} centered>
      <Modal.Header closeButton>
        <Modal.Title>Вход в аккаунт</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        Чтобы добавить в избранное, войдите или зарегистрируйтесь.
      </Modal.Body>
      <Modal.Footer>
        <a href="/login" className="btn btn-primary">Войти</a>
        <Button variant="secondary" onClick={onClose}>Закрыть</Button>
      </Modal.Footer>
    </Modal>
  );
};

export default LoginModal; 