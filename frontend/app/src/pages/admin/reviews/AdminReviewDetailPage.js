import React from 'react';
import { Container, Card, Button } from 'react-bootstrap';
import { useNavigate, useParams } from 'react-router-dom';
import ReviewDetail from '../../../components/reviews/ReviewDetail';
import { ROUTES } from '../../../utils/constants';

const AdminReviewDetailPage = () => {
  const navigate = useNavigate();
  const { id } = useParams();

  return (
    <Container className="py-4">
      <Card className="shadow-sm mb-4">
        <Card.Header className="bg-primary text-white">
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">Управление отзывом</h5>
            <Button
              variant="light"
              size="sm"
              onClick={() => navigate(ROUTES.ADMIN_REVIEWS)}
            >
              <i className="bi bi-arrow-left me-1"></i>
              Вернуться к списку
            </Button>
          </div>
        </Card.Header>
        <Card.Body>
          <ReviewDetail id={id} isAdmin={true} />
        </Card.Body>
      </Card>
    </Container>
  );
};

export default AdminReviewDetailPage; 