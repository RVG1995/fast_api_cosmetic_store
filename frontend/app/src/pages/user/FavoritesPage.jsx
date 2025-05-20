import React, { useEffect, useState, useCallback } from 'react';
import { favoriteAPI, productAPI } from '../../utils/api';
import ProductCard from '../../components/product/ProductCard';
import Pagination from '../../components/common/Pagination';
import { useAuth } from '../../context/AuthContext';

const PAGE_SIZE = 12;

const FavoritesPage = () => {
  const { isAuthenticated } = useAuth();
  const [favorites, setFavorites] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchFavorites = useCallback(async (pageNum = 1) => {
    setLoading(true);
    try {
      const favs = await favoriteAPI.getFavorites();
      setFavorites(favs);
      setTotal(favs.length);
      // Получаем продукты по id
      const ids = favs.slice((pageNum-1)*PAGE_SIZE, pageNum*PAGE_SIZE).map(f => f.product_id);
      if (ids.length) {
        const prods = await productAPI.getProductsByIds(ids);
        setProducts(prods);
      } else {
        setProducts([]);
      }
    } catch (e) {
      setFavorites([]);
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) fetchFavorites(page);
  }, [isAuthenticated, page, fetchFavorites]);

  const handleToggleFavorite = async (productId, willBeFavorite) => {
    if (willBeFavorite) await favoriteAPI.addFavorite(productId);
    else await favoriteAPI.removeFavorite(productId);
    fetchFavorites(page);
  };

  return (
    <div className="container py-4">
      <h2 className="mb-4">Избранные товары</h2>
      {loading ? (
        <div>Загрузка...</div>
      ) : products.length === 0 ? (
        <div>Нет избранных товаров</div>
      ) : (
        <>
          <div className="row">
            {products.map(product => (
              <div className="col-md-4 mb-4" key={product.id}>
                <ProductCard
                  product={product}
                  isFavorite={true}
                  onToggleFavorite={handleToggleFavorite}
                />
              </div>
            ))}
          </div>
          <Pagination
            currentPage={page}
            totalPages={Math.ceil(total / PAGE_SIZE)}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
};

export default FavoritesPage; 