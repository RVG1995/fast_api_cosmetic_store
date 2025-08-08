import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import PropTypes from 'prop-types';

const PublicOnlyRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (user) {
    return <Navigate to="/user" />;
  }

  return children;
};

export default PublicOnlyRoute; 

PublicOnlyRoute.propTypes = {
  children: PropTypes.node.isRequired,
};