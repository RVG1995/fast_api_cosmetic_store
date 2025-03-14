import { Navigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import LoadingSpinner from '../LoadingSpinner';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, isAdmin, isSuperAdmin } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  // Проверка прав доступа
  if (requireSuperAdmin && !isSuperAdmin()) {
    return <Navigate to="/" />;
  }
  
  if (!isAdmin()) {
    return <Navigate to="/" />;
  }

  return children;
};

export default AdminRoute;
