import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { favoriteAPI } from "../utils/api";

const FavoritesContext = createContext();

export const FavoritesProvider = ({ children }) => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchFavorites = useCallback(async () => {
    setLoading(true);
    try {
      const data = await favoriteAPI.getFavorites();
      setFavorites(data);
      setError(null);
    } catch (e) {
      setError(e);
      setFavorites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFavorites();
  }, [fetchFavorites]);

  const addFavorite = async (productId) => {
    await favoriteAPI.addFavorite(productId);
    setFavorites((prev) => [...prev, { product_id: productId }]);
  };

  const removeFavorite = async (productId) => {
    await favoriteAPI.removeFavorite(productId);
    setFavorites((prev) => prev.filter(f => f.product_id !== productId));
  };

  const isFavorite = (productId) => favorites.some(f => f.product_id === productId);

  return (
    <FavoritesContext.Provider value={{
      favorites,
      loading,
      error,
      fetchFavorites,
      addFavorite,
      removeFavorite,
      isFavorite,
    }}>
      {children}
    </FavoritesContext.Provider>
  );
};

export const useFavorites = () => useContext(FavoritesContext);