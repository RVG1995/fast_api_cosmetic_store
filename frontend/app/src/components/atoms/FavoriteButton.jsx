import { useFavorites } from '../../context/FavoritesContext';
import { useAuth } from '../../context/AuthContext';
import { useState } from 'react';

const FavoriteButton = ({ productId, disabled }) => {
  const { isFavorite, addFavorite, removeFavorite, loading } = useFavorites();
  const { isAuthenticated, openLoginModal } = useAuth();

  const handleClick = async (e) => {
    e.preventDefault();
    if (loading) return;
    if (!isAuthenticated) {
      if (openLoginModal) openLoginModal();
      else alert('Войдите или зарегистрируйтесь, чтобы добавлять в избранное');
      return;
    }
    if (isFavorite(productId)) await removeFavorite(productId);
    else await addFavorite(productId);
  };

  return (
    <button
      aria-label={isFavorite(productId) ? 'Убрать из избранного' : 'Добавить в избранное'}
      onClick={handleClick}
      disabled={loading || disabled}
      className="p-1 bg-transparent border-0 focus:outline-none"
      tabIndex={0}
      type="button"
    >
      {isFavorite(productId)
        ? <i className="bi bi-heart-fill text-danger fs-4"></i>
        : <i className="bi bi-heart text-secondary fs-4"></i>}
    </button>
  );
};

export default FavoriteButton; 