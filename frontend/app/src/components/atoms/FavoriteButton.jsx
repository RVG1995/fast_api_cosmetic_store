import { useState } from 'react';
import PropTypes from 'prop-types';

const FavoriteButton = ({ isFavorite, onToggle, productId, disabled }) => {
  const [loading, setLoading] = useState(false);
  const handleClick = async (e) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    await onToggle(productId, !isFavorite);
    setLoading(false);
  };
  return (
    <button
      aria-label={isFavorite ? 'Убрать из избранного' : 'Добавить в избранное'}
      onClick={handleClick}
      disabled={loading || disabled}
      className="p-1 bg-transparent border-0 focus:outline-none"
      tabIndex={0}
      type="button"
    >
      {isFavorite
        ? <i className="bi bi-heart-fill text-danger fs-4"></i>
        : <i className="bi bi-heart text-secondary fs-4"></i>}
    </button>
  );
};

FavoriteButton.propTypes = {
  isFavorite: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  productId: PropTypes.number.isRequired,
  disabled: PropTypes.bool,
};

export default FavoriteButton; 