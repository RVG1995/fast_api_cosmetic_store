import { useFavorites } from '../../context/FavoritesContext';

const FavoriteButton = ({ productId, disabled }) => {
  const { isFavorite, addFavorite, removeFavorite, loading } = useFavorites();

  const handleClick = async (e) => {
    e.preventDefault();
    if (loading) return;
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