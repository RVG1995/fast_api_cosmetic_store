import React, { useEffect, useState } from 'react';
import { productAPI } from '../../utils/api';
import ProductCard from '../../components/product/ProductCard';
import Pagination from '../../components/common/Pagination';
import { useFavorites } from '../../context/FavoritesContext';

const PAGE_SIZE = 12;

const FavoritesPage = () => {
  const { favorites, loading: favLoading, addFavorite, removeFavorite } = useFavorites();
  const [products, setProducts] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const ids = favorites.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE).map(f => f.product_id);
    setTotal(favorites.length);
    if (ids.length) {
      productAPI.getProductsByIds(ids).then(setProducts);
    } else {
      setProducts([]);
    }
  }, [favorites, page]);

  const handleToggleFavorite = async (productId) => {
    if (favorites.some(f => f.product_id === productId)) await removeFavorite(productId);
    else await addFavorite(productId);
  };

  return (
    <div className="container py-4">
      <h2 className="mb-4">Избранные товары</h2>
      {favLoading ? (
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