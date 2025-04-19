import React, { createContext, useContext, useState } from 'react';
import { Modal, Button } from 'react-bootstrap';

const ConfirmContext = createContext();
export const useConfirm = () => useContext(ConfirmContext);

const ConfirmModal = ({ title, body, onConfirm, onCancel }) => (
  <Modal show centered onHide={onCancel}>
    <Modal.Header closeButton>
      <Modal.Title>{title}</Modal.Title>
    </Modal.Header>
    <Modal.Body>{body}</Modal.Body>
    <Modal.Footer>
      <Button variant="secondary" onClick={onCancel}>Нет</Button>
      <Button variant="danger" onClick={onConfirm}>Да</Button>
    </Modal.Footer>
  </Modal>
);

export const ConfirmProvider = ({ children }) => {
  const [options, setOptions] = useState(null);
  const confirm = ({ title, body }) =>
    new Promise(resolve => {
      setOptions({
        title,
        body,
        onConfirm: () => { setOptions(null); resolve(true); },
        onCancel:  () => { setOptions(null); resolve(false); }
      });
    });

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {options && <ConfirmModal {...options} />}
    </ConfirmContext.Provider>
  );
}; 