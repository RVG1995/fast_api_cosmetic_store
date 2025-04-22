import React from 'react';
import { Button } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';

const AdminBackButton = ({ to, label, variant = 'outline-primary', className = '' }) => {
  const navigate = useNavigate();
  return (
    <Button
      variant={variant}
      onClick={() => navigate(to)}
      className={`mb-3 ${className}`}
    >
      <i className="bi bi-arrow-left me-1"></i>
      {label}
    </Button>
  );
};

AdminBackButton.propTypes = {
  to: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  variant: PropTypes.string,
  className: PropTypes.string,
};

export default AdminBackButton; 